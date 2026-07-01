"""Metadata collection and caching for historical data."""

import asyncio
from collections import OrderedDict
from datetime import date
from time import monotonic
from typing import TYPE_CHECKING

from lsst.ts.rubintv.background.metadata_streamer import MetadataStreamer
from lsst.ts.rubintv.config import config, rubintv_logger
from lsst.ts.rubintv.models.models import MetadataRefData, ServiceTypes
from lsst.ts.rubintv.models.models_helpers import date_str_to_date, find_first

if TYPE_CHECKING:
    from lsst.ts.rubintv.models.models import Camera, Location
    from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger(__name__)


class MetadataCollector:
    """Manages historical metadata collection with LRU caching and prefetching.

    Provides caching with LRU (Least Recently Used) eviction policy, background
    prefetching, and synchronization to prevent duplicate S3 fetches.
    """

    # Default maximum days of metadata to cache in memory per loc_cam.
    # The effective value is read from config in ``__init__`` (env var
    # ``RUBINTV_METADATA_CACHE_DAYS``) and set on the instance, so this class
    # attribute is only the fallback default.
    METADATA_CACHE_DAYS = 60

    def __init__(
        self, s3_clients: dict[str, "S3Client"], locations: list["Location"]
    ) -> None:
        """Initialize the metadata collector.

        Parameters
        ----------
        s3_clients : `dict`[`str`, `S3Client`]
            Dictionary mapping location names to S3 client instances.
        locations : `list`[`Location`]
            List of location objects.
        """
        self._s3_clients = s3_clients
        self._locations = locations

        # Effective cache cap, sourced from config so it can be tuned via the
        # RUBINTV_METADATA_CACHE_DAYS env var without a code change. Shadows
        # the class-level default. Guard against a non-positive value that
        # would otherwise evict every entry immediately.
        self.METADATA_CACHE_DAYS = max(1, config.metadata_cache_days)

        # Metadata refs tracking available dates for each loc_cam
        self._metadata_refs: dict[str, set[MetadataRefData]] = {}
        # Structure: {loc_cam: {MetadataRefData(date_str, hash), ...}}

        # Metadata cache using OrderedDict for LRU behavior
        self._metadata_cache: dict[str, OrderedDict[str, dict]] = {}
        # Structure: {loc_cam: OrderedDict({date_str: metadata_dict})}

        # Background prefetch control
        self._metadata_prefetch_task: asyncio.Task | None = None
        self._prefetch_paused = asyncio.Event()
        self._active_requests = 0
        self._request_lock = asyncio.Lock()

        # Per-key locks to prevent duplicate fetches
        self._fetch_locks: dict[str, asyncio.Lock] = {}

        # Semaphore to throttle background S3 fetches (prefetch and watcher).
        # Foreground requests bypass this semaphore entirely so they are never
        # blocked behind an in-flight background fetch.
        self.background_fetch_semaphore = asyncio.Semaphore(1)

    @property
    def metadata_refs(self) -> dict[str, set[MetadataRefData]]:
        """Get the metadata refs dictionary."""
        return self._metadata_refs

    def register_metadata_ref(
        self, loc_cam: str, date_str: str, metadata_hash: str
    ) -> None:
        """Register that metadata exists for a location/camera/date
        combination.

        Parameters
        ----------
        loc_cam : `str`
            Location and camera identifier (format: "location/camera").
        date_str : `str`
            ISO format date string.
        hash : `str`
            Metadata hash from bucket.
        """
        self._metadata_refs.setdefault(loc_cam, set()).add(
            MetadataRefData(date_str=date_str, metadata_hash=metadata_hash)
        )
        logger.debug(
            f"Registered metadata ref for {loc_cam} on {date_str} with hash {metadata_hash}"
        )

    async def get_metadata_for_date(
        self, location: "Location", camera: "Camera", date_str: str
    ) -> dict | None:
        """Get metadata for a specific date with caching.

        Fetches metadata from cache if available, otherwise retrieves from S3
        and caches the result. Uses per-key locks to prevent duplicate S3
        fetches.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.

        Returns
        -------
        metadata : `dict` | `None`
            The metadata dictionary, or None if not found or error occurred.
        """
        t_request = monotonic()
        logger.debug(
            f"Requesting metadata for {location.name}/{camera.name} on {date_str}"
        )
        loc_cam = f"{location.name}/{camera.name}"

        if not await self.metadata_exists_for_date(location, camera, date_str):
            logger.debug(f"Metadata does not exist for {loc_cam} on {date_str}")
            return None

        # Initialize cache for this loc_cam if needed
        if loc_cam not in self._metadata_cache:
            self._metadata_cache[loc_cam] = OrderedDict()

        cache = self._metadata_cache[loc_cam]

        # Check cache first
        if date_str in cache:
            # Move to end (mark as recently used)
            cache.move_to_end(date_str)
            return cache[date_str]

        # Use per-key lock to prevent duplicate fetches
        cache_key = f"{loc_cam}/{date_str}"
        if cache_key not in self._fetch_locks:
            self._fetch_locks[cache_key] = asyncio.Lock()

        async with self._fetch_locks[cache_key]:
            # Double-check cache after acquiring lock
            if date_str in cache:
                cache.move_to_end(date_str)
                return cache[date_str]

            t_lock_acquired = monotonic()
            logger.debug(
                f"Metadata lock acquired for {loc_cam}/{date_str} "
                f"(lock_wait={t_lock_acquired - t_request:.2f}s)"
            )

            # Track active request and pause prefetch if needed
            async with self._request_lock:
                self._active_requests += 1
                if self._active_requests == 1:
                    # First active request - pause prefetch
                    self._prefetch_paused.set()

            # Fetch from S3
            try:
                metadata = await self._fetch_metadata_from_s3(
                    location, camera, date_str
                )
                t_fetched = monotonic()
                logger.debug(
                    f"Metadata S3 fetch complete for {loc_cam}/{date_str} "
                    f"(fetch_time={t_fetched - t_lock_acquired:.2f}s, "
                    f"total_time={t_fetched - t_request:.2f}s, "
                    f"found={bool(metadata)})"
                )
                if metadata:
                    # Add to cache
                    cache[date_str] = metadata

                    # Maintain cache size limit
                    while len(cache) > self.METADATA_CACHE_DAYS:
                        cache.popitem(last=False)  # Remove oldest

                    # Move to end (mark as recently used)
                    cache.move_to_end(date_str)

                    logger.debug(f"Cached metadata for {loc_cam}/{date_str}")

                return metadata

            except Exception as e:
                logger.error(f"Failed to fetch metadata for {loc_cam}/{date_str}: {e}")
                return None
            finally:
                # Resume background prefetch when no active requests
                async with self._request_lock:
                    self._active_requests -= 1
                    if self._active_requests == 0:
                        # No more active requests - resume prefetch
                        self._prefetch_paused.clear()

    async def _fetch_metadata_from_s3(
        self,
        location: "Location",
        camera: "Camera",
        date_str: str,
        use_semaphore: bool = False,
    ) -> dict | None:
        """Fetch metadata from S3 for a specific date.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.
        use_semaphore : `bool`, optional
            If True, acquire ``_prefetch_semaphore`` before fetching.  Set by
            background prefetch to throttle concurrent S3 requests.  Foreground
            requests pass ``False`` (the default) so they are never blocked
            behind an in-flight prefetch.

        Returns
        -------
        metadata : `dict` | `None`
            The metadata dictionary, or None if not found or error occurred.
        """
        client = self._s3_clients[location.name]
        key = f"{camera.name}/{date_str}/metadata.json"

        async def _do_fetch() -> dict | None:
            t0 = monotonic()
            metadata = await client.async_get_object(key)
            elapsed = monotonic() - t0
            size_kb = len(str(metadata)) / 1024 if metadata else 0
            logger.debug(
                f"S3 get_object: key={key} time={elapsed:.2f}s size={size_kb:.1f}KB"
            )
            return metadata

        try:
            if use_semaphore:
                async with self.background_fetch_semaphore:
                    return await _do_fetch()
            else:
                return await _do_fetch()
        except Exception:
            return None

    async def start_prefetch(self, locations: list["Location"]) -> None:
        """Start background metadata prefetching.

        Parameters
        ----------
        locations : `list`[`Location`]
            List of location objects to prefetch metadata for.
        """
        if self._metadata_prefetch_task and not self._metadata_prefetch_task.done():
            self._metadata_prefetch_task.cancel()
            try:
                await self._metadata_prefetch_task
            except asyncio.CancelledError:
                pass

        self._prefetch_paused.clear()
        self._metadata_prefetch_task = asyncio.create_task(
            self._background_metadata_prefetch(locations)
        )

    async def _background_metadata_prefetch(self, locations: list["Location"]) -> None:
        """Background task to prefetch metadata for the last 60 days.

        Parameters
        ----------
        locations : `list`[`Location`]
            List of location objects to prefetch metadata for.
        """
        try:
            logger.info("Starting background metadata prefetch")

            for location in locations:
                await self._prefetch_location_metadata(location)

            logger.info("Background metadata prefetch completed")

        except asyncio.CancelledError:
            logger.info("Metadata prefetch cancelled")
        except Exception as e:
            logger.error(f"Error in background metadata prefetch: {e}")

    async def _prefetch_location_metadata(self, location: "Location") -> None:
        """Prefetch metadata for all cameras in a location.

        Parameters
        ----------
        location : `Location`
            The location object.
        """
        for camera in location.cameras:
            if not camera.online:
                continue

            loc_cam = f"{location.name}/{camera.name}"

            # Initialize cache for this loc_cam if needed
            if loc_cam not in self._metadata_cache:
                self._metadata_cache[loc_cam] = OrderedDict()

            cache = self._metadata_cache[loc_cam]

            # Get all available metadata dates for this camera, sorted newest
            # first
            available_dates: list[str] = []
            if loc_cam in self._metadata_refs:
                just_dates = [ref.date_str for ref in self._metadata_refs[loc_cam]]
                available_dates = sorted(
                    just_dates,
                    key=lambda d: date_str_to_date(d),
                    reverse=True,
                )

            # Prefetch up to last 60 found metadata files, skipping already
            # cached dates
            prefetch_count = 0
            for date_str in available_dates:
                # Pause prefetch if there are active requests
                while self._prefetch_paused.is_set():
                    await asyncio.sleep(0.1)

                if date_str in cache:
                    continue

                if prefetch_count >= self.METADATA_CACHE_DAYS:
                    break

                # Use per-key lock to prevent duplicate fetches
                cache_key = f"{loc_cam}/{date_str}"
                if cache_key not in self._fetch_locks:
                    self._fetch_locks[cache_key] = asyncio.Lock()

                async with self._fetch_locks[cache_key]:
                    # Double-check cache after acquiring lock
                    if date_str in cache:
                        continue

                    try:
                        t_prefetch = monotonic()
                        metadata = await self._fetch_metadata_from_s3(
                            location, camera, date_str, use_semaphore=True
                        )
                        if metadata:
                            # Add to cache (will be inserted at end due to
                            # OrderedDict)
                            cache[date_str] = metadata
                            # Move to end to mark as recently accessed
                            cache.move_to_end(date_str)

                            logger.debug(
                                f"Prefetched metadata for {loc_cam}/{date_str} "
                                f"(fetch_time={monotonic() - t_prefetch:.2f}s)"
                            )
                            prefetch_count += 1

                            # Small delay to prevent overwhelming S3
                            await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.debug(
                            f"Failed to prefetch metadata for {loc_cam}/{date_str}: {e}"
                        )

            if prefetch_count > 0:
                logger.info(f"Prefetched {prefetch_count} metadata files for {loc_cam}")

    async def shift_cache_for_new_day(self) -> None:
        """Shift the metadata cache when a new day rolls over."""
        for _, cache in self._metadata_cache.items():
            if len(cache) >= self.METADATA_CACHE_DAYS:
                # Remove oldest entries to make room
                while len(cache) >= self.METADATA_CACHE_DAYS:
                    cache.popitem(last=False)  # Remove oldest (FIFO)

    async def clear_cache(self) -> None:
        """Explicitly clear the metadata cache and refs."""
        logger.info("Clearing metadata cache and refs")
        self._metadata_refs.clear()
        for loc_cam in self._metadata_cache:
            self._metadata_cache[loc_cam].clear()
        self._fetch_locks.clear()

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        if self._metadata_prefetch_task and not self._metadata_prefetch_task.done():
            self._metadata_prefetch_task.cancel()
            try:
                await self._metadata_prefetch_task
            except asyncio.CancelledError:
                pass

    def cache_metadata(self, loc_cam: str, date_str: str, metadata: dict) -> None:
        """Store *metadata* in the LRU cache for *loc_cam*/*date_str*."""
        if loc_cam not in self._metadata_cache:
            self._metadata_cache[loc_cam] = OrderedDict()
        cache = self._metadata_cache[loc_cam]
        cache[date_str] = metadata
        cache.move_to_end(date_str)
        while len(cache) > self.METADATA_CACHE_DAYS:
            cache.popitem(last=False)

    def get_cached_metadata(
        self, location: "Location", camera: "Camera", date_str: str
    ) -> dict | None:
        """Return metadata for a date only if already in cache.

        Unlike :meth:`get_metadata_for_date`, this never triggers an S3
        fetch.  Returns ``None`` when the data is not cached.
        """
        loc_cam = f"{location.name}/{camera.name}"
        cache = self._metadata_cache.get(loc_cam)
        if cache is None or date_str not in cache:
            return None
        cache.move_to_end(date_str)
        return cache[date_str]

    async def metadata_exists_for_date(
        self, location: "Location", camera: "Camera", date_str: str
    ) -> bool:
        """Check if metadata exists for a specific date.

        Parameters
        ----------
        location : `Location`
            The location object.
        camera : `Camera`
            The camera object.
        date_str : `str`
            ISO format date string.

        Returns
        -------
        exists : `bool`
            True if metadata exists, False otherwise.
        """
        loc_cam = f"{location.name}/{camera.name}"
        if loc_cam not in self._metadata_refs:
            return False
        just_dates = {ref.date_str for ref in self._metadata_refs[loc_cam]}
        return date_str in just_dates

    async def check_for_changed_metadata(self, yesterday: date | None = None) -> None:
        """Check S3 for changed metadata files and update refs and cache
        accordingly.

        Parameters
        ----------
        yesterday : `date`, optional
            If provided, only check metadata for the specified date. Default
            is None (check all dates in refs).
        """
        # cycle through all metadata refs for this loc_cam and check if the
        # hash has changed
        logger.info("Checking for changed metadata files")
        for loc_cam, refs in self._metadata_refs.items():
            # Get client by location
            location_name, camera_name = loc_cam.split("/", 1)
            location = find_first(
                self._locations,
                "name",
                location_name,
            )
            if not location:
                logger.error(f"Location {location_name} not found for metadata check")
                continue
            camera = find_first(
                location.cameras,
                "name",
                camera_name,
            )
            if not camera:
                logger.error(
                    f"Camera {camera_name} not found in location {location_name} for metadata check"
                )
                continue
            client = self._s3_clients[location_name]
            if yesterday is not None:
                # Filter refs to only check the specified date
                refs = {ref for ref in refs if ref.date_str == yesterday.isoformat()}
                if not refs:
                    logger.debug(
                        f"No metadata refs for {loc_cam} on {yesterday.isoformat()} to check"
                    )
                    continue
            for ref in list(refs):
                key = f"{camera_name}/{ref.date_str}/metadata.json"
                try:
                    logger.debug(f"Checking metadata for {loc_cam} on {ref.date_str}")
                    objs = await client.async_list_objects(key)
                    if not objs:
                        # removed metadata file - remove ref and cache entry
                        logger.info(
                            f"Metadata file removed for {loc_cam} on {ref.date_str}, "
                            "removing ref and cache entry"
                        )
                        refs.remove(ref)
                        if (
                            loc_cam in self._metadata_cache
                            and ref.date_str in self._metadata_cache[loc_cam]
                        ):
                            del self._metadata_cache[loc_cam][ref.date_str]
                        continue

                    obj = objs[0]
                    new_hash = obj.get("hash")
                    if not new_hash or new_hash == ref.metadata_hash:
                        continue

                    logger.info(
                        f"Metadata changed for {loc_cam} on {ref.date_str}, "
                        f"updating hash from {ref.metadata_hash} to {new_hash}"
                    )

                    # Update the hash in refs only when changed.
                    logger.debug(
                        f"Updating metadata ref for {loc_cam} on {ref.date_str} with new hash {new_hash}"
                    )
                    self._metadata_refs[loc_cam].remove(ref)
                    self._metadata_refs[loc_cam].add(
                        MetadataRefData(date_str=ref.date_str, metadata_hash=new_hash)
                    )

                    # Invalidate cached metadata for this date so next read
                    # fetches the updated object.
                    if (
                        loc_cam in self._metadata_cache
                        and ref.date_str in self._metadata_cache[loc_cam]
                    ):
                        del self._metadata_cache[loc_cam][ref.date_str]

                    # Stream the new metadata in chunks to subscribed clients
                    # and update the local cache with the result.
                    key = f"{camera_name}/{ref.date_str}/metadata.json"
                    streamer = MetadataStreamer(client)
                    metadata = await streamer.stream_to_service(
                        key=key,
                        loc_cam=loc_cam,
                        service=ServiceTypes.HISTORICALDATAUPDATE,
                    )
                    if not metadata:
                        # No subscribers or fetch failed; fall back to plain
                        # fetch so the cache stays warm.
                        metadata = await self._fetch_metadata_from_s3(
                            location, camera, ref.date_str
                        )
                except Exception as e:
                    logger.error(
                        f"Error checking metadata for {loc_cam} on {ref.date_str}: {e}"
                    )
                finally:
                    # Yield to the event loop between each S3 check to avoid
                    # saturating the endpoint and blocking foreground requests.
                    await asyncio.sleep(0.1)
