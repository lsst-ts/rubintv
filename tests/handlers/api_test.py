import asyncio

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import Camera, Location, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.mark.asyncio
async def test_get_api_locations(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    client, _, _ = mocked_client
    """Test that root api gives data for every location"""
    response = await client.get("/rubintv/api/")
    data = response.json()
    assert data == [loc.model_dump() for loc in m.locations]


@pytest.mark.asyncio
async def test_get_api_location(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location gives data for a particular location"""
    client, _, _ = mocked_client
    location_name = "slac"
    location: Location | None = find_first(m.locations, "name", location_name)
    assert location is not None
    response = await client.get(f"/rubintv/api/{location_name}")
    data = response.json()
    assert data == location.model_dump()


@pytest.mark.asyncio
async def test_get_invalid_api_location(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location returns 404 for a non-existent location"""
    client, _, _ = mocked_client
    location_name = "ramona"
    response = await client.get(f"/rubintv/api/{location_name}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_api_location_camera(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location camera gives data for a particular camera"""
    client, _, _ = mocked_client
    location_name = "summit-usdf"
    camera_name = "startracker_wide"
    location: Location | None = find_first(m.locations, "name", location_name)
    assert location is not None
    cameras = location.cameras
    camera: Camera | None = find_first(cameras, "name", camera_name)
    assert camera is not None
    response = await client.get(f"/rubintv/api/{location_name}/{camera_name}")
    data = response.json()
    assert data == [location.model_dump(), camera.model_dump()]


@pytest.mark.asyncio
async def test_get_invalid_api_location_camera(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location returns 404 for a camera not at an existing
    location"""
    client, _, _ = mocked_client
    location_name = "summit-usdf"
    camera_name = "ts8"
    response = await client.get(f"/rubintv/api/{location_name}/{camera_name}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_api_location_camera_current_for_offline(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location camera current gives no events for offline
    camera"""
    client, _, _ = mocked_client

    location_name = "summit-usdf"
    location: Location | None = find_first(m.locations, "name", location_name)
    assert location is not None
    for camera in location.cameras:
        if not camera.online:
            response = await client.get(
                f"/rubintv/api/{location_name}/{camera.name}/current"
            )
            data = response.json()
            assert data == {}


@pytest.mark.asyncio
async def test_get_api_camera_for_today(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker],
) -> None:
    """Test that api location/camera/current day obs yields a result"""
    client, app, _ = mocked_client

    hp: HistoricalPoller = app.state.historical
    while await hp.is_busy():
        await asyncio.sleep(0.1)

    today = get_current_day_obs()
    response = await client.get(f"/rubintv/api/slac/lsstcam/date/{today}")
    data = response.json()
    assert "channelData" in data
    assert data["channelData"] != {}
