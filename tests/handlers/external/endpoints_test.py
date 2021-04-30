"""Tests for the rubintv.handlers.external.index module and routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rubintv.app import create_app

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def test_get_table(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/table")
    assert response.status == 200
