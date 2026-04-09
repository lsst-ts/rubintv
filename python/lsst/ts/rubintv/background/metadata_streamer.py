"""Streaming delivery of metadata files to WebSocket clients."""

import asyncio
import base64
import gzip
import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, AsyncGenerator
from uuid import UUID

from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs

if TYPE_CHECKING:
    from fastapi import WebSocket
    from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger(__name__)

# Size of each raw-bytes chunk read from S3.
STREAM_CHUNK_SIZE = 256 * 1024  # 256 KB


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

    def __init__(self, s3_client: "S3Client") -> None:
        self._s3_client = s3_client
        self.result: dict[str, Any] = {}

    async def stream_to_service(
        self,
        key: str,
        loc_cam: str,
        service: Service,
        notify_latest: bool = False,
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

        Returns
        -------
        metadata : `dict`[`str`, `Any`]
            The fully parsed metadata dictionary, or an empty dict if the
            object could not be fetched or there are no subscribers.
        """
        service_key = f"{service.value} {loc_cam}"
        client_ids = await self._get_client_ids(service_key)
        if not client_ids:
            return {}

        websockets = await self._get_websockets(client_ids)
        if not websockets:
            return {}

        raw_chunks: list[bytes] = []
        try:
            async for chunk in self._iter_raw_chunks(key):
                raw_chunks.append(chunk)
                await self._broadcast_chunk(websockets, service, chunk, final=False)
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

        # Signal end-of-stream with a final empty chunk marker, then send the
        # full parsed payload so clients can commit it to their state.
        await self._broadcast_chunk(websockets, service, b"", final=True)
        await self._broadcast_full(
            websockets, service, MessageType.CAMERA_METADATA, metadata
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
        body = await loop.run_in_executor(executor, self._s3_client.get_raw_object, key)
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

    async def _broadcast_chunk(
        self,
        websockets: list["WebSocket"],
        service: Service,
        chunk: bytes,
        final: bool,
    ) -> None:
        """Compress, encode and broadcast a single raw chunk to all clients."""
        datestamp = get_current_day_obs().isoformat()
        encoded = base64.b64encode(gzip.compress(chunk)).decode("utf-8")
        message = {
            "service": service.value,
            "dataType": MessageType.METADATA_CHUNK.value,
            "payload": encoded,
            "final": final,
            "datestamp": datestamp,
        }
        tasks = [ws.send_json(message) for ws in websockets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for exc in results:
            if isinstance(exc, Exception):
                logger.warning(
                    "Failed to send metadata chunk to client", error=str(exc)
                )

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
        tasks = [ws.send_json(message) for ws in websockets]
        await asyncio.gather(*tasks, return_exceptions=True)

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
        client_ids = await self._get_client_ids(service_key)
        if not client_ids:
            return

        websockets = await self._get_websockets(client_ids)
        if not websockets:
            return

        await self._broadcast_full(
            websockets, service, MessageType.CAMERA_METADATA, metadata
        )
        if notify_latest:
            latest = self._get_last_entry(metadata)
            if latest:
                await self._broadcast_full(
                    websockets, service, MessageType.LATEST_METADATA, latest
                )

    @staticmethod
    def _get_last_entry(metadata: dict) -> dict:
        """Return a dict containing only the last (highest) seq-num entry."""
        if not metadata:
            return {}
        last_seq = str(max(int(k) for k in metadata.keys()))
        return {last_seq: metadata[last_seq]}
