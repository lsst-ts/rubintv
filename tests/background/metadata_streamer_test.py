"""Tests for MetadataStreamer and send_metadata_chunks."""

import asyncio
import base64
import gzip
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from lsst.ts.rubintv.background.metadata_streamer import (
    STREAM_CHUNK_SIZE,
    MetadataStreamer,
    _stream_locks,
    send_metadata_chunks,
)
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metadata(num_entries: int = 5) -> dict[str, Any]:
    """Create a small metadata dict for testing."""
    return {
        str(i): {"seq_num": i, "exposure_time": 30.0, "filter": "r"}
        for i in range(num_entries)
    }


def _make_large_metadata(target_bytes: int = STREAM_CHUNK_SIZE * 3) -> dict[str, Any]:
    """Create metadata large enough to require multiple chunks."""
    metadata: dict[str, Any] = {}
    i = 0
    while len(json.dumps(metadata).encode()) < target_bytes:
        metadata[str(i)] = {
            "seq_num": i,
            "exposure_time": 30.0,
            "filter": "r",
            "padding": "x" * 500,
        }
        i += 1
    return metadata


def _decode_chunk_payload(payload: str) -> bytes:
    """Reverse the gzip+base64 encoding applied to a chunk payload."""
    return gzip.decompress(base64.b64decode(payload))


async def _register_mock_subscriber(
    service_key: str,
) -> tuple[AsyncMock, Any]:
    """Register a mock websocket as a subscriber and return (ws, client_id)."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    cid = uuid4()
    async with clients_lock:
        clients[cid] = ws
        websocket_to_client[ws] = cid
    async with services_lock:
        services_clients.setdefault(service_key, []).append(cid)
    return ws, cid


async def _cleanup_subscribers() -> None:
    """Remove all registered subscribers."""
    async with clients_lock:
        clients.clear()
        websocket_to_client.clear()
    async with services_lock:
        services_clients.clear()
    _stream_locks.clear()


def _make_s3_client_mock(metadata: dict[str, Any]) -> MagicMock:
    """Create a mock S3Client that returns the given metadata."""
    raw = json.dumps(metadata).encode("utf-8")
    s3 = MagicMock()

    async def get_object_info(key: str) -> dict[str, Any]:
        return {"ContentLength": len(raw)}

    s3.get_object_info = AsyncMock(side_effect=get_object_info)

    # get_raw_object returns a file-like object whose .read(n) yields chunks.
    body = MagicMock()
    _offset = [0]

    def read_chunk(n: int) -> bytes:
        start = _offset[0]
        chunk = raw[start : start + n]
        _offset[0] = start + n
        return chunk

    body.read = MagicMock(side_effect=read_chunk)
    s3.get_raw_object = MagicMock(return_value=body)

    return s3


# ---------------------------------------------------------------------------
# send_metadata_chunks tests
# ---------------------------------------------------------------------------


class TestSendMetadataChunks:
    @pytest.mark.asyncio
    async def test_small_metadata_single_chunk_plus_final(self) -> None:
        """Small metadata should produce one data chunk + one final chunk."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        metadata = _make_metadata(3)

        await send_metadata_chunks(ws, metadata, Service.CAMERA)

        calls = ws.send_json.call_args_list
        # One data chunk + one final
        assert len(calls) == 2

        data_msg = calls[0].args[0]
        assert data_msg["dataType"] == MessageType.METADATA_CHUNK.value
        assert data_msg["final"] is False
        assert data_msg["service"] == Service.CAMERA.value
        assert data_msg["totalSize"] > 0
        assert data_msg["bytesSent"] == data_msg["totalSize"]

        final_msg = calls[1].args[0]
        assert final_msg["final"] is True
        assert final_msg["bytesSent"] == final_msg["totalSize"]

    @pytest.mark.asyncio
    async def test_large_metadata_multiple_chunks(self) -> None:
        """Metadata larger than STREAM_CHUNK_SIZE produces multiple chunks."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        metadata = _make_large_metadata()
        raw_size = len(json.dumps(metadata).encode())

        await send_metadata_chunks(ws, metadata, Service.CAMERA)

        calls = ws.send_json.call_args_list
        # At least 3 data chunks + 1 final
        assert len(calls) >= 4

        # All non-final chunks have final=False
        for call in calls[:-1]:
            msg = call.args[0]
            assert msg["final"] is False
            assert msg["totalSize"] == raw_size

        # Last chunk is the final signal
        final = calls[-1].args[0]
        assert final["final"] is True
        assert final["bytesSent"] == raw_size

    @pytest.mark.asyncio
    async def test_chunk_payloads_reassemble_to_original(self) -> None:
        """Decoding and concatenating chunk payloads reproduces the JSON."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        metadata = _make_large_metadata()

        await send_metadata_chunks(ws, metadata, Service.CAMERA)

        calls = ws.send_json.call_args_list
        parts: list[bytes] = []
        for call in calls:
            msg = call.args[0]
            if not msg["final"]:
                parts.append(_decode_chunk_payload(msg["payload"]))

        reassembled = b"".join(parts)
        assert json.loads(reassembled) == metadata

    @pytest.mark.asyncio
    async def test_bytes_sent_is_cumulative(self) -> None:
        """bytesSent should increase with each chunk."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        metadata = _make_large_metadata()

        await send_metadata_chunks(ws, metadata, Service.CAMERA)

        calls = ws.send_json.call_args_list
        prev_bytes = 0
        for call in calls[:-1]:
            msg = call.args[0]
            assert msg["bytesSent"] > prev_bytes
            prev_bytes = msg["bytesSent"]


# ---------------------------------------------------------------------------
# MetadataStreamer tests
# ---------------------------------------------------------------------------


class TestMetadataStreamer:
    @pytest_asyncio.fixture(autouse=True)
    async def _cleanup(self) -> Any:
        """Clean up global state after each test."""
        yield
        await _cleanup_subscribers()

    @pytest.mark.asyncio
    async def test_stream_to_service_no_subscribers_still_fetches(self) -> None:
        """With no subscribers, S3 data is still fetched and parsed
        (the watcher needs it for caching), but nothing is broadcast."""
        metadata = _make_metadata()
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        result = await streamer.stream_to_service(
            key="cam/2026-01-01/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )
        assert result == metadata
        assert streamer.result == metadata

    @pytest.mark.asyncio
    async def test_stream_to_service_broadcasts_chunks(self) -> None:
        """Subscribers receive data chunks + final chunk."""
        metadata = _make_metadata(5)
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="cam/2026-01-01/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )

        assert result == metadata
        assert streamer.result == metadata

        calls = ws.send_json.call_args_list
        assert len(calls) >= 2  # at least 1 data chunk + 1 final

        # Last call should be the final chunk
        final = calls[-1].args[0]
        assert final["final"] is True

    @pytest.mark.asyncio
    async def test_stream_to_service_chunks_reassemble(self) -> None:
        """Reassembling broadcast chunks produces the original metadata."""
        metadata = _make_large_metadata()
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        await streamer.stream_to_service(
            key="cam/2026-01-01/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )

        calls = ws.send_json.call_args_list
        parts: list[bytes] = []
        for call in calls:
            msg = call.args[0]
            if msg["dataType"] == MessageType.METADATA_CHUNK.value and not msg["final"]:
                parts.append(_decode_chunk_payload(msg["payload"]))

        assert json.loads(b"".join(parts)) == metadata

    @pytest.mark.asyncio
    async def test_stream_to_service_returns_empty_on_missing_object(self) -> None:
        """Returns {} when the S3 object doesn't exist."""
        s3 = MagicMock()
        s3.get_object_info = AsyncMock(return_value=None)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="missing.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_stream_to_service_returns_empty_on_no_content_length(self) -> None:
        """Returns {} when object info has no ContentLength."""
        s3 = MagicMock()
        s3.get_object_info = AsyncMock(return_value={"ETag": "abc"})
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="bad.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_cache_check_skips_s3_fetch(self) -> None:
        """When cache_check returns data, S3 is not called."""
        cached = _make_metadata(3)
        s3 = MagicMock()
        s3.get_object_info = AsyncMock()
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
            cache_check=lambda: cached,
        )

        assert result == cached
        s3.get_object_info.assert_not_awaited()
        # Client should still receive chunks (from _send_parsed)
        assert ws.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_cache_check_none_proceeds_with_fetch(self) -> None:
        """When cache_check returns None, S3 fetch proceeds normally."""
        metadata = _make_metadata(3)
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
            cache_check=lambda: None,
        )

        assert result == metadata
        s3.get_object_info.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notify_latest_sends_last_entry(self) -> None:
        """With notify_latest=True, a LATEST_METADATA message is sent."""
        metadata = _make_metadata(5)
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
            notify_latest=True,
        )

        calls = ws.send_json.call_args_list
        latest_msgs = [
            c.args[0]
            for c in calls
            if c.args[0].get("dataType") == MessageType.LATEST_METADATA.value
        ]
        assert len(latest_msgs) == 1
        payload = json.loads(
            gzip.decompress(base64.b64decode(latest_msgs[0]["payload"]))
        )
        # Should contain only the highest seq num
        assert "4" in payload
        assert len(payload) == 1

    @pytest.mark.asyncio
    async def test_notify_parsed_sends_chunks_to_subscribers(self) -> None:
        """notify_parsed sends chunk messages from pre-parsed data."""
        metadata = _make_metadata(5)
        s3 = MagicMock()
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CHANNEL.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        await streamer.notify_parsed(
            metadata=metadata,
            loc_cam="loc/cam",
            service=Service.CHANNEL,
        )

        calls = ws.send_json.call_args_list
        assert len(calls) >= 2

        # Verify data can be reassembled
        parts: list[bytes] = []
        for call in calls:
            msg = call.args[0]
            if msg["dataType"] == MessageType.METADATA_CHUNK.value and not msg["final"]:
                parts.append(_decode_chunk_payload(msg["payload"]))
        assert json.loads(b"".join(parts)) == metadata

    @pytest.mark.asyncio
    async def test_notify_parsed_with_latest(self) -> None:
        """notify_parsed with notify_latest sends LATEST_METADATA."""
        metadata = _make_metadata(10)
        s3 = MagicMock()
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CHANNEL.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        await streamer.notify_parsed(
            metadata=metadata,
            loc_cam="loc/cam",
            service=Service.CHANNEL,
            notify_latest=True,
        )

        calls = ws.send_json.call_args_list
        latest_msgs = [
            c.args[0]
            for c in calls
            if c.args[0].get("dataType") == MessageType.LATEST_METADATA.value
        ]
        assert len(latest_msgs) == 1

    @pytest.mark.asyncio
    async def test_notify_parsed_no_subscribers_is_noop(self) -> None:
        """notify_parsed with no subscribers sends nothing."""
        metadata = _make_metadata()
        s3 = MagicMock()
        streamer = MetadataStreamer(s3)

        # No subscribers registered — should complete without error
        await streamer.notify_parsed(
            metadata=metadata,
            loc_cam="loc/cam",
            service=Service.CHANNEL,
        )

    @pytest.mark.asyncio
    async def test_dead_websocket_is_removed(self) -> None:
        """A websocket that errors during broadcast is unregistered."""
        metadata = _make_metadata()
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"

        # Good websocket
        ws_good, cid_good = await _register_mock_subscriber(service_key)
        # Bad websocket — send_json raises
        ws_bad, cid_bad = await _register_mock_subscriber(service_key)
        ws_bad.send_json = AsyncMock(side_effect=ConnectionError("gone"))

        await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )

        # Good ws received messages
        assert ws_good.send_json.call_count > 0

        # Bad ws should be unregistered from global state
        async with clients_lock:
            assert cid_bad not in clients

    @pytest.mark.asyncio
    async def test_stream_lock_prevents_interleaving(self) -> None:
        """Two concurrent streams for the same key are serialised by the
        lock."""
        metadata = _make_metadata(3)
        s3 = _make_s3_client_mock(metadata)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        order: list[str] = []

        original_do_stream = MetadataStreamer._do_stream

        async def slow_do_stream(self_inner: Any, *args: Any, **kwargs: Any) -> Any:
            order.append("start")
            await asyncio.sleep(0.05)
            result = await original_do_stream(self_inner, *args, **kwargs)
            order.append("end")
            return result

        MetadataStreamer._do_stream = slow_do_stream  # type: ignore[assignment]
        try:
            streamer1 = MetadataStreamer(s3)
            streamer2 = MetadataStreamer(_make_s3_client_mock(metadata))

            t1 = asyncio.create_task(
                streamer1.stream_to_service(
                    key="cam/metadata.json",
                    loc_cam="loc/cam",
                    service=Service.CAMERA,
                )
            )
            t2 = asyncio.create_task(
                streamer2.stream_to_service(
                    key="cam/metadata.json",
                    loc_cam="loc/cam",
                    service=Service.CAMERA,
                )
            )
            await asyncio.gather(t1, t2)

            # Streams should be serialised: start, end, start, end
            assert order == ["start", "end", "start", "end"]
        finally:
            MetadataStreamer._do_stream = original_do_stream  # type: ignore[assignment]

    @pytest.mark.asyncio
    async def test_get_last_entry(self) -> None:
        """_get_last_entry returns only the highest seq-num key."""
        metadata = _make_metadata(10)
        result = MetadataStreamer._get_last_entry(metadata)
        assert list(result.keys()) == ["9"]
        assert result["9"] == metadata["9"]

    @pytest.mark.asyncio
    async def test_get_last_entry_empty(self) -> None:
        """_get_last_entry on empty dict returns empty dict."""
        assert MetadataStreamer._get_last_entry({}) == {}

    @pytest.mark.asyncio
    async def test_chunk_total_size_and_bytes_sent(self) -> None:
        """Every chunk message carries correct totalSize and bytesSent."""
        metadata = _make_large_metadata()
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)
        raw_size = len(json.dumps(metadata).encode())

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws, _ = await _register_mock_subscriber(service_key)

        await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )

        calls = ws.send_json.call_args_list
        chunk_msgs = [
            c.args[0]
            for c in calls
            if c.args[0].get("dataType") == MessageType.METADATA_CHUNK.value
        ]

        prev_bytes = 0
        for msg in chunk_msgs:
            assert msg["totalSize"] == raw_size
            assert msg["bytesSent"] >= prev_bytes
            prev_bytes = msg["bytesSent"]

        # Final chunk should have bytesSent == totalSize
        assert chunk_msgs[-1]["bytesSent"] == raw_size
        assert chunk_msgs[-1]["final"] is True

    @pytest.mark.asyncio
    async def test_semaphore_is_respected(self) -> None:
        """When a semaphore is provided, it limits concurrent S3 access."""
        metadata = _make_metadata(3)
        s3 = _make_s3_client_mock(metadata)
        sem = asyncio.Semaphore(1)
        streamer = MetadataStreamer(s3, semaphore=sem)

        service_key = f"{Service.CAMERA.value} loc/cam"
        await _register_mock_subscriber(service_key)

        result = await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )
        # Semaphore should not prevent the stream from completing
        assert result == metadata

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_receive_chunks(self) -> None:
        """All subscribers receive the same chunk messages."""
        metadata = _make_metadata(5)
        s3 = _make_s3_client_mock(metadata)
        streamer = MetadataStreamer(s3)

        service_key = f"{Service.CAMERA.value} loc/cam"
        ws1, _ = await _register_mock_subscriber(service_key)
        ws2, _ = await _register_mock_subscriber(service_key)

        await streamer.stream_to_service(
            key="cam/metadata.json",
            loc_cam="loc/cam",
            service=Service.CAMERA,
        )

        # Both should have received the same number of messages
        assert ws1.send_json.call_count == ws2.send_json.call_count
        assert ws1.send_json.call_count >= 2
