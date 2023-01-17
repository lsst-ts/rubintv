"""Tests for the rubintv.handlers.external.index module and routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aiohttp import web

from rubintv.app import create_app

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


@pytest.mark.asyncio
async def request_heartbeat_for_auxtel_monitor(
    aiohttp_client: TestClient,
) -> None:
    """Test GET /app-name/summit/heartbeat/auxtel_monitor"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response: web.Response = await client.get(
        f"/{name}/summit/heartbeat/auxtel_monitor"
    )
    assert response.status == 200
    assert response.content_type == "application/json"


@pytest.mark.asyncio
async def test_get_index(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/")
    assert response.status == 200


@pytest.mark.asyncio
async def test_admin_page(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/admin"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/admin")
    assert response.status == 200


@pytest.mark.asyncio
async def test_reload_historical(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/reload_historical
    Reloads all historical data from the bucket"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.post(f"/{name}/summit/reload_historical")
    assert response.status == 200
    text = await response.text()
    assert text == "OK"


@pytest.mark.asyncio
async def request_all_heartbeats(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/heartbeats"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/heartbeats")
    assert response.status == 200
    assert response.content_type == "application/json"


@pytest.mark.asyncio
async def request_heartbeat_for_unknown_channel(
    aiohttp_client: TestClient,
) -> None:
    """Test GET /app-name/summit/heartbeat/none-existant"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/heartbeat/non-existant")
    assert response.status == 404


@pytest.mark.asyncio
async def test_get_allsky_page(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky
    All Sky has its own page not based on the general camera
    page template or endpoint"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_allsky_image_update(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky/update/image"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky/update/image")
    assert response.status == 200
    assert response.content_type == "application/json"


@pytest.mark.asyncio
async def test_get_allsky_movie_update(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky/update/movie"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky/update/movie")
    assert response.status == 200
    assert response.content_type == "application/json"


@pytest.mark.asyncio
async def test_get_allsky_historical(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky/historical"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky/historical")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_allsky_movie_for_date(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky/historical/2022-12-15"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky/historical/2022-12-15")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_allsky_movie_for_badly_formed_date(
    aiohttp_client: TestClient,
) -> None:
    """Test GET /app-name/summit/allsky/historical/111-111-111"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(
        f"/{name}/summit/allsky/historical/111-111-111"
    )
    assert response.status == 404


@pytest.mark.asyncio
async def test_get_camera_page(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/camera-name"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/auxtel")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_camera_page_fail(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/none"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/none")
    # Expect this to fail since "none" is not a camera endpoint/slug
    assert response.status == 404


@pytest.mark.asyncio
async def test_get_camera_update(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/update/
    Should respond with two-part json object with keys 'table'
    and 'per-day'"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/auxtel/update")
    assert response.status == 200
    assert response.content_type == "application/json"


@pytest.mark.asyncio
async def test_camera_imevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/imevents/2022-04-05"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(
        f"/{name}/summit/auxtel/imevents/2022-04-05/929"
    )
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_specevents(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/specevents/2022-02-08/163"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(
        f"/{name}/summit/auxtel/specevents/2022-02-08/163"
    )
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_imcurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/im_current"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/summit/auxtel/im_current")
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_speccurrent(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/spec_current"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/summit/auxtel/spec_current")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_camera_historical(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/camera-name/historical"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/auxtel/historical")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_camera_historical_date(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/camera-name/historical/2022-02-23"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/auxtel/historical/2022-02-23")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_camera_historical_for_badly_formed_date(
    aiohttp_client: TestClient,
) -> None:
    """Test GET /app-name/summit/auxtel/historical/111-111-111"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(
        f"/{name}/summit/auxtel/historical/111-111-111"
    )
    assert response.status == 404
