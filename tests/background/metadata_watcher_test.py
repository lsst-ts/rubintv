"""Tests for MetadataWatcher."""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from lsst.ts.rubintv.background.metadata_streamer import _stream_locks
from lsst.ts.rubintv.background.metadata_watcher import MetadataWatcher
from lsst.ts.rubintv.handlers.websockets_clients import (
    clients,
    clients_lock,
    services_clients,
    services_lock,
    websocket_to_client,
)
from lsst.ts.rubintv.models.models_init import ModelsInitiator

m = ModelsInitiator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metadata(num_entries: int = 5) -> dict[str, Any]:
    return {
        str(i): {"seq_num": i, "exposure_time": 30.0, "filter": "r"}
        for i in range(num_entries)
    }


def _make_s3_client_mock(metadata: dict[str, Any]) -> MagicMock:
    """Mock S3Client that returns metadata from get_raw_object."""
    raw = json.dumps(metadata).encode("utf-8")
    s3 = MagicMock()

    async def get_object_info(key: str) -> dict[str, Any]:
        return {"ContentLength": len(raw)}

    s3.get_object_info = AsyncMock(side_effect=get_object_info)

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


async def _cleanup_global_state() -> None:
    async with clients_lock:
        clients.clear()
        websocket_to_client.clear()
    async with services_lock:
        services_clients.clear()
    _stream_locks.clear()


def _get_test_location_and_camera() -> tuple:
    """Return a (location, camera) from test config."""
    location = m.locations[0]
    camera = location.cameras[0]
    return location, camera


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetadataWatcher:
    @pytest_asyncio.fixture(autouse=True)
    async def _cleanup(self) -> Any:
        yield
        await _cleanup_global_state()

    def _make_watcher(
        self,
        metadata: dict[str, Any] | None = None,
        metadata_store: dict[str, dict] | None = None,
    ) -> tuple[MetadataWatcher, MagicMock]:
        """Build a MetadataWatcher with a mock S3 client."""
        location, camera = _get_test_location_and_camera()
        md = metadata or _make_metadata()
        s3_mock = _make_s3_client_mock(md)
        store = metadata_store if metadata_store is not None else {}
        watcher = MetadataWatcher(
            locations=m.locations,
            s3_clients={location.name: s3_mock},
            metadata_store=store,
        )
        return watcher, s3_mock

    # -- notify_pending ---------------------------------------------------

    def test_notify_pending_adds_to_pending(self) -> None:
        watcher, _ = self._make_watcher()
        watcher.notify_pending("loc/cam", {"key": "k", "hash": "h1"})
        assert "loc/cam" in watcher._pending

    def test_notify_pending_deduplicates_by_etag(self) -> None:
        """Same ETag after a successful fetch is a no-op."""
        watcher, _ = self._make_watcher()
        watcher._fetched_hashes["loc/cam"] = "h1"
        watcher.notify_pending("loc/cam", {"key": "k", "hash": "h1"})
        assert "loc/cam" not in watcher._pending

    def test_notify_pending_accepts_new_etag(self) -> None:
        """A new ETag after a previous fetch is accepted."""
        watcher, _ = self._make_watcher()
        watcher._fetched_hashes["loc/cam"] = "h1"
        watcher.notify_pending("loc/cam", {"key": "k", "hash": "h2"})
        assert "loc/cam" in watcher._pending

    # -- clear ------------------------------------------------------------

    def test_clear_resets_state(self) -> None:
        watcher, _ = self._make_watcher()
        watcher._pending["loc/cam"] = {"key": "k", "hash": "h1"}
        watcher._fetched_hashes["loc/cam"] = "h1"
        watcher.clear()
        assert len(watcher._pending) == 0
        assert len(watcher._fetched_hashes) == 0

    # -- _resolve ---------------------------------------------------------

    def test_resolve_valid_loc_cam(self) -> None:
        watcher, _ = self._make_watcher()
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"
        resolved_loc, resolved_cam = watcher._resolve(loc_cam)
        assert resolved_loc is not None
        assert resolved_cam is not None
        assert resolved_loc.name == location.name
        assert resolved_cam.name == camera.name

    def test_resolve_invalid_loc_cam(self) -> None:
        watcher, _ = self._make_watcher()
        loc, cam = watcher._resolve("nonexistent/camera")
        assert loc is None or cam is None

    def test_resolve_malformed_string(self) -> None:
        watcher, _ = self._make_watcher()
        loc, cam = watcher._resolve("no-slash-here")
        assert loc is None
        assert cam is None

    # -- _drain_pending ---------------------------------------------------

    @pytest.mark.asyncio
    async def test_drain_pending_empty_is_noop(self) -> None:
        watcher, _ = self._make_watcher()
        assert len(watcher._pending) == 0
        await watcher._drain_pending()
        # Nothing should happen

    @pytest.mark.asyncio
    async def test_drain_pending_clears_pending(self) -> None:
        watcher, _ = self._make_watcher()
        watcher._pending["loc/cam"] = {"key": "k", "hash": "h1"}
        await watcher._drain_pending()
        assert len(watcher._pending) == 0

    @pytest.mark.asyncio
    async def test_drain_pending_marks_fetched_hash(self) -> None:
        watcher, _ = self._make_watcher()
        watcher._pending["loc/cam"] = {"key": "k", "hash": "h1"}
        await watcher._drain_pending()
        assert watcher._fetched_hashes.get("loc/cam") == "h1"

    # -- _fetch_and_stream ------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_and_stream_caches_metadata(self) -> None:
        """Successful fetch writes to metadata_store."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"
        metadata = _make_metadata(3)
        store: dict[str, dict] = {}
        watcher, _ = self._make_watcher(metadata=metadata, metadata_store=store)

        key = f"{camera.name}/2026-01-01/metadata.json"
        await watcher._fetch_and_stream(loc_cam, {"key": key, "hash": "h1"})

        assert loc_cam in store
        assert store[loc_cam] == metadata

    @pytest.mark.asyncio
    async def test_fetch_and_stream_unknown_loc_cam_logs_error(self) -> None:
        """Unknown loc_cam doesn't crash, returns without caching."""
        store: dict[str, dict] = {}
        watcher, _ = self._make_watcher(metadata_store=store)

        await watcher._fetch_and_stream("nonexistent/cam", {"key": "k", "hash": "h1"})
        assert len(store) == 0

    @pytest.mark.asyncio
    async def test_fetch_and_stream_empty_data_clears_hash(self) -> None:
        """When S3 returns empty data, the fetched hash is cleared for
        retry."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"

        s3 = MagicMock()
        s3.get_object_info = AsyncMock(return_value=None)

        store: dict[str, dict] = {}
        watcher = MetadataWatcher(
            locations=m.locations,
            s3_clients={location.name: s3},
            metadata_store=store,
        )
        watcher._fetched_hashes[loc_cam] = "h1"

        await watcher._fetch_and_stream(loc_cam, {"key": "k", "hash": "h1"})

        # Hash should be cleared so the next poll retries
        assert loc_cam not in watcher._fetched_hashes

    @pytest.mark.asyncio
    async def test_fetch_and_stream_exception_clears_hash(self) -> None:
        """An exception during fetch clears the hash for retry."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"

        s3 = MagicMock()
        s3.get_object_info = AsyncMock(side_effect=RuntimeError("boom"))

        store: dict[str, dict] = {}
        watcher = MetadataWatcher(
            locations=m.locations,
            s3_clients={location.name: s3},
            metadata_store=store,
        )
        watcher._fetched_hashes[loc_cam] = "h1"

        await watcher._fetch_and_stream(loc_cam, {"key": "k", "hash": "h1"})

        assert loc_cam not in watcher._fetched_hashes

    @pytest.mark.asyncio
    async def test_fetch_and_stream_does_not_update_unchanged_metadata(self) -> None:
        """If metadata hasn't changed, the store is not updated."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"
        metadata = _make_metadata(3)
        store: dict[str, dict] = {loc_cam: metadata}
        watcher, _ = self._make_watcher(metadata=metadata, metadata_store=store)

        key = f"{camera.name}/2026-01-01/metadata.json"
        await watcher._fetch_and_stream(loc_cam, {"key": key, "hash": "h1"})

        # Store should still reference the same dict object (not replaced)
        assert store[loc_cam] is metadata

    # -- fan-out to metadata_from cameras ---------------------------------

    @pytest.mark.asyncio
    async def test_fan_out_notifies_dependent_cameras(self) -> None:
        """Cameras with metadata_from pointing to the fetched camera
        receive notify_parsed calls."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"
        metadata = _make_metadata(3)
        store: dict[str, dict] = {}
        watcher, _ = self._make_watcher(metadata=metadata, metadata_store=store)

        # Find cameras that depend on this camera's metadata
        dependent = [c for c in location.cameras if c.metadata_from == camera.name]

        key = f"{camera.name}/2026-01-01/metadata.json"

        with patch(
            "lsst.ts.rubintv.background.metadata_watcher.MetadataStreamer"
        ) as MockStreamer:
            mock_instance = MagicMock()
            mock_instance.stream_to_service = AsyncMock(return_value=metadata)
            mock_instance.notify_parsed = AsyncMock()
            MockStreamer.return_value = mock_instance

            await watcher._fetch_and_stream(loc_cam, {"key": key, "hash": "h1"})

            # notify_parsed should be called for the camera itself + dependents
            expected_calls = 1 + len(dependent)
            assert mock_instance.notify_parsed.call_count == expected_calls

    # -- start / stop -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        """Start creates a task, stop cancels it."""
        watcher, _ = self._make_watcher()
        task = watcher.start()
        assert not task.done()

        # Let the loop run briefly
        await asyncio.sleep(0.1)

        watcher.stop()
        # Give the task time to notice cancellation
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass
        assert task.done()

    @pytest.mark.asyncio
    async def test_run_drains_pending(self) -> None:
        """The background loop processes pending entries."""
        location, camera = _get_test_location_and_camera()
        loc_cam = f"{location.name}/{camera.name}"
        metadata = _make_metadata(3)
        store: dict[str, dict] = {}
        watcher, _ = self._make_watcher(metadata=metadata, metadata_store=store)

        key = f"{camera.name}/2026-01-01/metadata.json"
        watcher.notify_pending(loc_cam, {"key": key, "hash": "h1"})

        task = watcher.start()
        # Wait enough for the watcher loop to drain
        await asyncio.sleep(1.5)
        watcher.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass

        assert loc_cam in store

    @pytest.mark.asyncio
    async def test_stop_idempotent(self) -> None:
        """Calling stop when not started doesn't raise."""
        watcher, _ = self._make_watcher()
        watcher.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_stop_after_done(self) -> None:
        """Calling stop after task is already done is safe."""
        watcher, _ = self._make_watcher()
        task = watcher.start()
        watcher.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass
        watcher.stop()  # Second stop should not raise
