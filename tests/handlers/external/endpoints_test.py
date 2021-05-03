"""Tests for the rubintv.handlers.external.index module and routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rubintv.app import create_app

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def test_get_index(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/")
    assert response.status == 200


async def test_get_index_num(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/?num=10")
    assert response.status == 200


async def test_get_index_num_fail(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/?num=hello")
    # Expect this to fail since "hello" can't be coerced to an int
    assert response.status == 500


async def test_imevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/imevents/2021-03-23/327")
    assert response.status == 200


async def test_specevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/specevents/2021-03-23/327")
    assert response.status == 200


async def test_imcurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/im_current")
    assert response.status == 200


async def test_speccurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/spec_current")
    assert response.status == 200
