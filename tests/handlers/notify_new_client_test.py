"""Tests for ``notify_new_client`` in handlers/websocket.py.

These pin down two invariants for current-day metadata delivery:

1. When ``CurrentPoller.get_current_metadata`` returns data, it is sent
   via ``send_metadata_chunks``.
2. When ``CurrentPoller.get_current_metadata`` returns empty, the
   historical cache is **not** consulted as a fallback.  Historical data
   only covers up to yesterday, so checking it for today's metadata is
   semantically wrong and was removed in commit 9b5032dd.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lsst.ts.rubintv.handlers.websocket import notify_new_client
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models_init import ModelsInitiator

m = ModelsInitiator()


def _make_websocket_with_state(
    current_metadata: dict | None,
    historical_metadata: dict | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Build a fake WebSocket whose ``app.state`` carries a current poller
    and historical poller.

    Returns
    -------
    websocket : MagicMock
    historical : MagicMock
        Returned separately so tests can assert directly on
        ``historical.get_cached_metadata`` invocation.
    """
    ws = MagicMock()
    ws.send_json = AsyncMock()

    cp = MagicMock()
    cp.get_current_metadata = AsyncMock(return_value=current_metadata or {})

    async def empty_async_iter(*args: Any, **kwargs: Any) -> Any:
        # ``get_latest_data`` is an async generator; yield nothing so
        # ``async for`` exits immediately.
        return
        yield  # pragma: no cover  - unreachable, makes this a generator

    cp.get_latest_data = empty_async_iter

    historical = MagicMock()
    historical.get_cached_metadata = MagicMock(return_value=historical_metadata)

    ws.app.state.current_poller = cp
    ws.app.state.historical = historical
    return ws, historical


def _pick_camera_location() -> tuple:
    """Return a (location, camera) usable in tests.  Picks the first
    online camera that isn't a metadata_from dependent (so it owns its
    own metadata)."""
    for loc in m.locations:
        for cam in loc.cameras:
            if cam.online and not cam.metadata_from:
                return loc, cam
    raise RuntimeError("No online owning-metadata camera in test config")


@pytest.mark.asyncio
async def test_notify_new_client_sends_current_metadata_when_cached() -> None:
    """When the current poller has metadata, it is streamed to the
    client via ``send_metadata_chunks``."""
    location, camera = _pick_camera_location()
    metadata = {"0": {"seq_num": 0}}
    ws, historical = _make_websocket_with_state(current_metadata=metadata)

    with patch(
        "lsst.ts.rubintv.handlers.websocket.send_metadata_chunks",
        new=AsyncMock(),
    ) as mock_send:
        await notify_new_client(ws, location, camera, "", Service.CAMERA)

        mock_send.assert_awaited_once()
        call = mock_send.await_args
        assert call is not None
        sent_ws, sent_metadata, sent_service = call.args
        assert sent_ws is ws
        assert sent_metadata == metadata
        assert sent_service == Service.CAMERA

    # Historical fallback must NOT have been consulted at all.
    historical.get_cached_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_notify_new_client_does_not_fall_back_to_historical() -> None:
    """When current metadata is empty, the historical cache must NOT
    be consulted.

    Historical data only covers up to yesterday, so falling back to it
    for today's page is semantically wrong.  Even if a historical entry
    *would* have matched, no chunks should be sent and
    ``historical.get_cached_metadata`` should not be called.
    """
    location, camera = _pick_camera_location()
    # Configure historical to return data — if the fallback path still
    # exists, the test will detect it via either:
    # (a) historical.get_cached_metadata being called, or
    # (b) send_metadata_chunks being called with historical data.
    fallback_data = {"99": {"seq_num": 99, "from": "historical"}}
    ws, historical = _make_websocket_with_state(
        current_metadata={},
        historical_metadata=fallback_data,
    )

    with patch(
        "lsst.ts.rubintv.handlers.websocket.send_metadata_chunks",
        new=AsyncMock(),
    ) as mock_send:
        await notify_new_client(ws, location, camera, "", Service.CAMERA)

        mock_send.assert_not_awaited()

    historical.get_cached_metadata.assert_not_called()
