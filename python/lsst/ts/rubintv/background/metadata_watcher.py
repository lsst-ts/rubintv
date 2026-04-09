"""Background task that watches for new/changed metadata files and streams
them to WebSocket clients independently of the main poll loop."""

import asyncio
from typing import TYPE_CHECKING

from lsst.ts.rubintv.background.metadata_streamer import MetadataStreamer
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import ServiceTypes as Service

if TYPE_CHECKING:
    from lsst.ts.rubintv.models.models import Camera, Location
    from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger(__name__)

# How often the watcher checks for pending metadata fetches (seconds).
WATCH_INTERVAL = 0.5


class MetadataWatcher:
    """Watches for new or changed metadata files and streams them to
    WebSocket clients without blocking the main poll loop.

    The poll loop remains responsible only for discovering metadata objects
    via S3 listing and calling :meth:`notify_pending` when it finds one.
    This class owns everything that happens after that: fetching, streaming,
    writing back to the shared cache, and fan-out to cameras that share the
    same file (e.g. Star Trackers).

    Parameters
    ----------
    locations : `list`[`Location`]
        All configured locations, used to look up cameras and their
        ``metadata_from`` relationships.
    s3_clients : `dict`[`str`, `S3Client`]
        S3 client instances keyed by location name.
    metadata_store : `dict`[`str`, `dict`]
        Shared reference to ``CurrentPoller._metadata``.  The watcher writes
        parsed metadata into it after each successful fetch so that
        ``get_current_metadata`` and ``get_latest_data`` see it.
    """

    def __init__(
        self,
        locations: list["Location"],
        s3_clients: dict[str, "S3Client"],
        metadata_store: dict[str, dict],
    ) -> None:
        self._locations = locations
        self._s3_clients = s3_clients
        self._metadata_store = metadata_store

        # Pending metadata objects keyed by loc_cam.  The poll loop writes
        # here via notify_pending(); the watcher drains it.
        # Value: {"key": s3_key, "hash": etag}
        self._pending: dict[str, dict[str, str]] = {}

        # ETags that have already been successfully fetched, used to skip
        # re-fetching when the same object appears in successive poll cycles.
        self._fetched_hashes: dict[str, str] = {}

        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> asyncio.Task:
        """Start the background watcher task and return it."""
        self._task = asyncio.create_task(self._run())
        return self._task

    def stop(self) -> None:
        """Cancel the background watcher task."""
        if self._task and not self._task.done():
            self._task.cancel()

    def clear(self) -> None:
        """Reset state on day rollover so all metadata is re-fetched for the
        new day."""
        self._pending.clear()
        self._fetched_hashes.clear()

    def notify_pending(self, loc_cam: str, md_obj: dict[str, str]) -> None:
        """Register a metadata object as pending a fetch.

        Called by the poll loop when it discovers a metadata.json in the
        S3 listing.  If the ETag matches a previously completed fetch the
        call is a no-op.

        Parameters
        ----------
        loc_cam : `str`
            Location/camera identifier, e.g. ``"usdf/lsstcam"``.
        md_obj : `dict`[`str`, `str`]
            Dict with ``"key"`` (S3 object key) and ``"hash"`` (ETag).
        """
        etag = md_obj["hash"]
        if self._fetched_hashes.get(loc_cam) == etag:
            return
        self._pending[loc_cam] = md_obj

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        logger.info("MetadataWatcher started")
        try:
            while True:
                await self._drain_pending()
                await asyncio.sleep(WATCH_INTERVAL)
        except asyncio.CancelledError:
            logger.info("MetadataWatcher stopped")

    async def _drain_pending(self) -> None:
        """Consume all pending entries, launching a task per loc_cam."""
        if not self._pending:
            return
        # Snapshot and clear atomically so the poll loop can add new entries
        # while tasks are in flight.
        snapshot, self._pending = self._pending, {}
        for loc_cam, md_obj in snapshot.items():
            # Mark fetched immediately so re-queued duplicates are dropped.
            self._fetched_hashes[loc_cam] = md_obj["hash"]
            asyncio.create_task(
                self._fetch_and_stream(loc_cam, md_obj),
                name=f"metadata-{loc_cam}",
            )

    async def _fetch_and_stream(self, loc_cam: str, md_obj: dict[str, str]) -> None:
        """Fetch, stream, and cache metadata for a single loc_cam."""
        location, camera = self._resolve(loc_cam)
        if location is None or camera is None:
            logger.error("MetadataWatcher: unknown loc_cam", loc_cam=loc_cam)
            return

        s3_client = self._s3_clients[location.name]
        streamer = MetadataStreamer(s3_client)

        data = await streamer.stream_to_service(
            key=md_obj["key"],
            loc_cam=loc_cam,
            service=Service.CAMERA,
        )

        if not data:
            return

        if loc_cam not in self._metadata_store or data != self._metadata_store[loc_cam]:
            self._metadata_store[loc_cam] = data
            logger.info("MetadataWatcher: cached metadata for", loc_cam=loc_cam)

        # Fan-out to cameras that share this metadata file
        # (e.g. Star Trackers).
        to_notify = [camera]
        to_notify.extend(c for c in location.cameras if c.metadata_from == camera.name)
        for cam in to_notify:
            cam_loc_cam = f"{location.name}/{cam.name}"
            await streamer.notify_parsed(
                metadata=data,
                loc_cam=cam_loc_cam,
                service=Service.CHANNEL,
                notify_latest=True,
            )

    def _resolve(self, loc_cam: str) -> tuple["Location | None", "Camera | None"]:
        """Look up Location and Camera objects from a loc_cam string."""
        parts = loc_cam.split("/", 1)
        if len(parts) != 2:
            return None, None
        location_name, camera_name = parts
        location = next(
            (loc for loc in self._locations if loc.name == location_name), None
        )
        if location is None:
            return None, None
        camera = next(
            (cam for cam in location.cameras if cam.name == camera_name), None
        )
        return location, camera
