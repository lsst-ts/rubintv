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


async def test_get_camera_page(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/camera-name"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/auxtel")
    assert response.status == 200


async def test_get_camera_page_fail(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/none"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/none")
    # Expect this to fail since "none" is not a camera endpoint/slug
    assert response.status == 404


async def test_camera_imevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/auxtel/imevents/2022-04-05"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/auxtel/imevents/2022-04-05/929")
    assert response.status == 200


async def test_camera_specevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/auxtel/specevents/2022-02-08/163"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/auxtel/specevents/2022-02-08/163")
    assert response.status == 200


async def test_camera_imcurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/auxtel/im_current"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/auxtel/im_current")
    assert response.status == 200


async def test_camera_speccurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/auxtel/spec_current"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/auxtel/spec_current")
    assert response.status == 200


async def test_get_camera_historical(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/camera-name/historical"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/auxtel/historical")
    assert response.status == 200


async def test_get_camera_historical_date(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/camera-name/historical/2022-02-23"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/auxtel/historical/2022-02-23")
    assert response.status == 200
