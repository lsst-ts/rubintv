"""Streaming delivery of metadata files to WebSocket clients."""

import asyncio
import base64
import gzip
import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable
from uuid import UUID

from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs

if TYPE_CHECKING:
    from fastapi import WebSocket
    from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger(__name__)

# Size of each raw-bytes chunk read from S3.
STREAM_CHUNK_SIZE = 128 * 1024  # 128 KB

# Per-service-key locks to prevent interleaved chunk streams to the
# same set of subscribers.
_stream_locks: dict[str, asyncio.Lock] = {}


async def send_metadata_chunks(
    websocket: "WebSocket",
    metadata: dict[str, Any],
    service: Service,
) -> None:
    """Send already-parsed metadata to a single websocket in chunks.

    Used by ``notify_new_client`` to stream cached metadata to a newly
    connected client so the frontend can show a progress bar.
    """
    raw = json.dumps(metadata).encode("utf-8")
    total_size = len(raw)
    logger.info(
        "send_metadata_chunks: starting",
        service=service.value,
        total_size=total_size,
        num_entries=len(metadata),
    )
    datestamp = get_current_day_obs().isoformat()
    cumulative_bytes = 0
    for offset in range(0, total_size, STREAM_CHUNK_SIZE):
        chunk = raw[offset : offset + STREAM_CHUNK_SIZE]
        cumulative_bytes += len(chunk)
        encoded = base64.b64encode(gzip.compress(chunk)).decode("utf-8")
        await websocket.send_json(
            {
                "service": service.value,
                "dataType": MessageType.METADATA_CHUNK.value,
                "payload": encoded,
                "final": False,
                "totalSize": total_size,
                "bytesSent": cumulative_bytes,
                "datestamp": datestamp,
            }
        )
    # Final (empty) chunk signals the client to reassemble.
    encoded = base64.b64encode(gzip.compress(b"")).decode("utf-8")
    await websocket.send_json(
        {
            "service": service.value,
            "dataType": MessageType.METADATA_CHUNK.value,
            "payload": encoded,
            "final": True,
            "totalSize": total_size,
            "bytesSent": total_size,
            "datestamp": datestamp,
        }
    )


class MetadataStreamer:
    """Streams a metadata JSON file from S3 to WebSocket clients in chunks.

    Instead of downloading the whole file, parsing it, re-serialising it and
    compressing it in one batch, this class:

    1. Opens a raw ``StreamingBody`` from S3 in a thread-pool worker.
    2. Reads it in ``STREAM_CHUNK_SIZE`` chunks, gzip-compressing and
       base64-encoding each one before broadcasting a ``METADATA_CHUNK``
       WebSocket message.
    3. After the last chunk, sends the reassembled and parsed dict as the
       familiar ``CAMERA_METADATA`` message so clients can commit state.
    4. Optionally sends a ``LATEST_METADATA`` message (last seq-num entry
       only) when *notify_latest* is requested.

    The parsed dict is stored on ``result`` after a successful stream so the
    caller can update its own in-memory cache without a second S3 round-trip.
    """

    def __init__(
        self,
        s3_client: "S3Client",
        semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        self._s3_client = s3_client
        self._semaphore = semaphore
        self.result: dict[str, Any] = {}

    async def stream_to_service(
        self,
        key: str,
        loc_cam: str,
        service: Service,
        notify_latest: bool = False,
        cache_check: "Callable[[], dict | None] | None" = None,
    ) -> dict[str, Any]:
        """Fetch *key* from S3 and stream it to all subscribers of *service*.

        Looks up all WebSocket clients subscribed to ``"{service} {loc_cam}"``
        (the same key used by :func:`notify_ws_clients`) and streams the
        metadata file to them in chunks, followed by the full parsed payload.

        Parameters
        ----------
        key : `str`
            S3 object key for the metadata JSON file.
        loc_cam : `str`
            Location/camera identifier, e.g. ``"usdf/lsstcam"``.
        service : `Service`
            Service enum value (``CAMERA`` or ``CHANNEL``) used both to
            resolve subscribers and to populate the WebSocket message envelope.
        notify_latest : `bool`, optional
            When ``True``, send a ``LATEST_METADATA`` message (last seq-num
            entry only) after the full ``CAMERA_METADATA`` message.  Useful
            for channel-scoped subscribers.
        cache_check : callable, optional
            If provided, called after the per-key lock is acquired.  When it
            returns a non-``None`` dict the S3 fetch is skipped and the
            cached data is sent via :meth:`notify_parsed` instead.

        Returns
        -------
        metadata : `dict`[`str`, `Any`]
            The fully parsed metadata dictionary, or an empty dict if the
            object could not be fetched or there are no subscribers.
        """
        service_key = f"{service.value} {loc_cam}"
        if service_key not in _stream_locks:
            _stream_locks[service_key] = asyncio.Lock()
        lock = _stream_locks[service_key]
        if lock.locked():
            logger.info(
                "stream_to_service: waiting for lock (another stream in progress)",
                service_key=service_key,
                key=key,
            )
        async with lock:
            # After acquiring the lock, check whether a preceding stream
            # already cached the data while we were waiting.
            if cache_check is not None:
                cached = cache_check()
                if cached is not None:
                    logger.info(
                        "stream_to_service: cache populated while waiting for lock, "
                        "sending cached data",
                        service_key=service_key,
                        key=key,
                    )
                    await self._send_parsed(
                        cached, loc_cam, service, service_key, notify_latest
                    )
                    return cached

            logger.info(
                "stream_to_service: lock acquired, starting stream",
                service_key=service_key,
                key=key,
            )
            result = await self._do_stream(
                key, loc_cam, service, service_key, notify_latest
            )
            logger.info(
                "stream_to_service: stream finished, releasing lock",
                service_key=service_key,
                key=key,
                has_result=bool(result),
            )
            return result

    async def _do_stream(
        self,
        key: str,
        loc_cam: str,
        service: Service,
        service_key: str,
        notify_latest: bool,
    ) -> dict[str, Any]:
        logger.debug(
            "Starting metadata stream",
            key=key,
            loc_cam=loc_cam,
            service=service.value,
        )
        raw_chunks: list[bytes] = []
        try:
            metadata_info = await self._s3_client.get_object_info(key)
            if metadata_info is None:
                logger.error(
                    "Metadata object not found in S3", key=key, loc_cam=loc_cam
                )
                return {}
            if "ContentLength" not in metadata_info:
                logger.error(
                    "Metadata object missing ContentLength", key=key, loc_cam=loc_cam
                )
                return {}
            metadata_size: int = metadata_info["ContentLength"]
            cumulative_bytes = 0
            async for chunk in self._iter_raw_chunks(key):
                raw_chunks.append(chunk)
                cumulative_bytes += len(chunk)
                # Resolve live websockets fresh for each chunk so that
                # clients who connected during the S3 fetch are included
                # and disconnected clients are skipped.
                websockets = await self._get_websockets(
                    await self._get_client_ids(service_key)
                )
                if websockets:
                    await self._broadcast_chunk(
                        websockets,
                        service,
                        chunk,
                        final=False,
                        total_size=metadata_size,
                        bytes_sent=cumulative_bytes,
                    )
        except Exception as e:
            logger.error(
                "Error streaming metadata chunks",
                key=key,
                loc_cam=loc_cam,
                error=str(e),
            )
            return {}

        # Reassemble and parse the full JSON.
        full_bytes = b"".join(raw_chunks)
        try:
            metadata: dict[str, Any] = json.loads(full_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(
                "Failed to parse streamed metadata JSON",
                key=key,
                loc_cam=loc_cam,
                error=str(e),
            )
            return {}

        self.result = metadata

        # Signal end-of-stream so clients can reassemble and commit.
        websockets = await self._get_websockets(await self._get_client_ids(service_key))
        if websockets:
            await self._broadcast_chunk(
                websockets,
                service,
                b"",
                final=True,
                total_size=metadata_size,
                bytes_sent=metadata_size,
            )

            if notify_latest:
                latest = self._get_last_entry(metadata)
                if latest:
                    await self._broadcast_full(
                        websockets, service, MessageType.LATEST_METADATA, latest
                    )

        logger.info(
            "Metadata streamed successfully",
            key=key,
            loc_cam=loc_cam,
            num_chunks=len(raw_chunks),
            total_bytes=len(full_bytes),
        )
        return metadata

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _iter_raw_chunks(self, key: str) -> AsyncGenerator[bytes, None]:
        """Async generator that yields raw bytes chunks from the S3 object."""
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        if self._semaphore is not None:
            async with self._semaphore:
                body = await loop.run_in_executor(
                    executor, self._s3_client.get_raw_object, key
                )
        else:
            body = await loop.run_in_executor(
                executor, self._s3_client.get_raw_object, key
            )
        while True:
            chunk: bytes = await loop.run_in_executor(
                executor, body.read, STREAM_CHUNK_SIZE
            )
            if not chunk:
                break
            yield chunk

    async def _get_client_ids(self, service_key: str) -> list[UUID]:
        """Return client IDs subscribed to *service_key*."""
        async with services_lock:
            return list(services_clients.get(service_key, []))

    async def _get_websockets(self, client_ids: list[UUID]) -> list["WebSocket"]:
        """Resolve client IDs to live WebSocket connections."""
        async with clients_lock:
            return [clients[cid] for cid in client_ids if cid in clients]

    async def _unregister_websockets(self, dead_ws: list["WebSocket"]) -> None:
        """Remove dead websockets from the global client/service registries.

        This prevents subsequent ``_get_client_ids`` / ``_get_websockets``
        calls from re-resolving connections that have already failed.
        """
        async with clients_lock:
            dead_ids: list[UUID] = []
            for ws in dead_ws:
                cid = websocket_to_client.pop(ws, None)
                if cid is not None:
                    clients.pop(cid, None)
                    dead_ids.append(cid)
        if dead_ids:
            async with services_lock:
                for id_list in services_clients.values():
                    for cid in dead_ids:
                        try:
                            id_list.remove(cid)
                        except ValueError:
                            pass
            logger.debug(
                "Unregistered dead websocket clients",
                count=len(dead_ids),
            )

    async def _broadcast_chunk(
        self,
        websockets: list["WebSocket"],
        service: Service,
        chunk: bytes,
        final: bool,
        total_size: int = 0,
        bytes_sent: int = 0,
    ) -> None:
        """Compress, encode and broadcast a single raw chunk to all clients.

        Websockets that fail are removed from *websockets* in place so
        that subsequent calls do not retry dead connections.
        """
        datestamp = get_current_day_obs().isoformat()
        encoded = base64.b64encode(gzip.compress(chunk)).decode("utf-8")
        message: dict[str, Any] = {
            "service": service.value,
            "dataType": MessageType.METADATA_CHUNK.value,
            "payload": encoded,
            "final": final,
            "totalSize": total_size,
            "bytesSent": bytes_sent,
            "datestamp": datestamp,
        }
        await self._broadcast_json(websockets, message)

    async def _broadcast_json(
        self,
        websockets: list["WebSocket"],
        message: dict[str, Any],
    ) -> None:
        tasks = [ws.send_json(message) for ws in websockets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failed: list[int] = []
        for idx, exc in enumerate(results):
            if isinstance(exc, Exception):
                logger.warning(
                    "Failed to send metadata chunk to client", error=str(exc)
                )
                failed.append(idx)
        if not failed:
            return
        # Collect the dead websockets, then remove them from the local
        # list *and* from the global client/service registries so that
        # subsequent re-resolution calls no longer return them.
        dead_ws = [websockets[idx] for idx in failed]
        for idx in reversed(failed):
            websockets.pop(idx)
        await self._unregister_websockets(dead_ws)

    async def _broadcast_full(
        self,
        websockets: list["WebSocket"],
        service: Service,
        message_type: MessageType,
        payload: Any,
    ) -> None:
        """Compress, encode and send a complete payload to all clients."""
        datestamp = get_current_day_obs().isoformat()
        encoded = base64.b64encode(
            gzip.compress(bytes(json.dumps(payload), "utf-8"))
        ).decode("utf-8")
        message = {
            "service": service.value,
            "dataType": message_type.value,
            "payload": encoded,
            "datestamp": datestamp,
        }
        await self._broadcast_json(websockets, message)

    async def notify_parsed(
        self,
        metadata: dict[str, Any],
        loc_cam: str,
        service: Service,
        notify_latest: bool = False,
    ) -> None:
        """Send already-parsed metadata to subscribers without an S3 fetch.

        Used when the data has already been retrieved (e.g. by a prior call to
        :meth:`stream_to_service`) and only needs to be forwarded to a
        different set of subscribers.

        Parameters
        ----------
        metadata : `dict`[`str`, `Any`]
            The fully parsed metadata dictionary.
        loc_cam : `str`
            Location/camera identifier used to resolve subscribers.
        service : `Service`
            Service enum value used both to resolve subscribers and to
            populate the WebSocket message envelope.
        notify_latest : `bool`, optional
            When ``True``, also send a ``LATEST_METADATA`` message.
        """
        service_key = f"{service.value} {loc_cam}"
        if service_key not in _stream_locks:
            _stream_locks[service_key] = asyncio.Lock()
        async with _stream_locks[service_key]:
            await self._send_parsed(
                metadata, loc_cam, service, service_key, notify_latest
            )

    async def _send_parsed(
        self,
        metadata: dict[str, Any],
        loc_cam: str,
        service: Service,
        service_key: str,
        notify_latest: bool,
    ) -> None:
        """Inner implementation of :meth:`notify_parsed` (no lock)."""
        client_ids = await self._get_client_ids(service_key)
        if not client_ids:
            return

        raw = json.dumps(metadata).encode("utf-8")
        total_size = len(raw)
        cumulative_bytes = 0
        for offset in range(0, total_size, STREAM_CHUNK_SIZE):
            chunk = raw[offset : offset + STREAM_CHUNK_SIZE]
            cumulative_bytes += len(chunk)
            websockets = await self._get_websockets(
                await self._get_client_ids(service_key)
            )
            if websockets:
                await self._broadcast_chunk(
                    websockets,
                    service,
                    chunk,
                    final=False,
                    total_size=total_size,
                    bytes_sent=cumulative_bytes,
                )

        websockets = await self._get_websockets(await self._get_client_ids(service_key))
        if websockets:
            await self._broadcast_chunk(
                websockets,
                service,
                b"",
                final=True,
                total_size=total_size,
                bytes_sent=total_size,
            )

            if notify_latest:
                latest = self._get_last_entry(metadata)
                if latest:
                    await self._broadcast_full(
                        websockets,
                        service,
                        MessageType.LATEST_METADATA,
                        latest,
                    )

    @staticmethod
    def _get_last_entry(metadata: dict) -> dict:
        """Return a dict containing only the last (highest) seq-num entry."""
        if not metadata:
            return {}
        last_seq = str(max(int(k) for k in metadata.keys()))
        return {last_seq: metadata[last_seq]}
