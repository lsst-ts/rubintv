"""Tests for the rubintv.handlers.external.index module and routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rubintv.app import create_app

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


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
async def test_get_allsky_page(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky")
    assert response.status == 200


@pytest.mark.asyncio
async def test_get_allsky_image_update(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/allsky/update/image"""
    app = create_app(load_minimal_data=True)
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
    json_data = await response.json()
    assert json_data["date"] == "2022-12-15"


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
    """Test GET /app-name/summit/allsky/historical/{date_to_load}"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    date_str = app["rubintv/date_to_load"]
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/allsky/historical/{date_str}")
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
    data = await response.json()
    assert list(data.keys()) == ["table", "per_day"]


@pytest.mark.asyncio
async def test_camera_im_event(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/im/event/{date_str}/549"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    date_str = app["rubintv/date_to_load"]
    client = await aiohttp_client(app)
    response = await client.get(
        f"/{name}/summit/auxtel/im/event/{date_str}/549"
    )
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_spec_event(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/spec/event/{date_str}/163"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    date_str = app["rubintv/date_to_load"]
    client = await aiohttp_client(app)
    response = await client.get(
        f"/{name}/summit/auxtel/spec/event/{date_str}/291"
    )
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_im_current(aiohttp_client: TestClient) -> None:
    """Test GET /app-name/summit/auxtel/im_current"""
    app = create_app()
    name = app["safir/config"].name
    client = await aiohttp_client(app)
    response = await client.get(f"/{name}/summit/auxtel/im_current")
    assert response.status == 200


@pytest.mark.asyncio
async def test_camera_spec_current(aiohttp_client: TestClient) -> None:
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
    """Test GET /app-name/summit/camera-name/historical/{date_str}"""
    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    date_str = app["rubintv/date_to_load"]
    client = await aiohttp_client(app)

    response = await client.get(f"/{name}/summit/auxtel/historical/{date_str}")
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


@pytest.mark.asyncio
async def test_heartbeats_websocket(aiohttp_client: TestClient) -> None:
    """Test websocket at /app-name/summit/heartbeats_ws
    Message sent should be same as contents of background
    heartbeat store
    """

    app = create_app(load_minimal_data=True)
    name = app["safir/config"].name
    client = await aiohttp_client(app)

    ws = await client.ws_connect(f"/{name}/summit/heartbeats_ws")
    message = await ws.receive_json()
    assert message == app["rubintv/heartbeats"]["summit"]
