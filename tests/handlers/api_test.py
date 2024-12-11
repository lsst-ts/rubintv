import asyncio

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import Camera, Event, Location, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import ModelsInitiator

from ..mockdata import RubinDataMocker

m = ModelsInitiator()


@pytest.mark.asyncio
async def test_get_api_locations(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    client, app, mocker = mocked_client
    """Test that root api gives data for every location"""
    response = await client.get("/rubintv/api/")
    data = response.json()
    assert data == [loc.model_dump() for loc in m.locations]


@pytest.mark.asyncio
async def test_get_api_location(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that api location gives data for a particular location"""
    client, app, mocker = mocked_client
    location_name = "slac"
    location: Location | None = find_first(m.locations, "name", location_name)
    assert location is not None
    response = await client.get(f"/rubintv/api/{location_name}")
    data = response.json()
    assert data == location.model_dump()


@pytest.mark.asyncio
async def test_get_invalid_api_location(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that api location returns 404 for a non-existent location"""
    client, app, mocker = mocked_client
    location_name = "ramona"
    response = await client.get(f"/rubintv/api/{location_name}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_api_location_camera(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that api location camera gives data for a particular camera"""
    client, app, mocker = mocked_client
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
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that api location returns 404 for a camera not at an existing
    location"""
    client, app, mocker = mocked_client
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
    client, app, mocker = mocked_client

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
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that api location/camera/current day obs yields a result"""
    client, app, mocker = mocked_client

    hp: HistoricalPoller = app.state.historical
    while await hp.is_busy():
        await asyncio.sleep(0.1)

    today = get_current_day_obs()
    response = await client.get(f"/rubintv/api/slac/slac_ts8/date/{today}")
    data = response.json()
    assert "channelData" in data
    assert data["channelData"] != {}


@pytest.mark.asyncio
async def test_get_camera_current_events(
    mocked_client: tuple[AsyncClient, FastAPI, RubinDataMocker]
) -> None:
    """Test that today's data is picked up"""
    client, app, mocker = mocked_client
    today = get_current_day_obs()
    camera: Camera | None = find_first(m.cameras, "name", "slac_lsstcam")
    assert camera is not None

    response = await client.get("/rubintv/api/slac/slac_lsstcam/current")
    data = response.json()

    assert data["date"] == today.isoformat()

    # check the table is in descending order of seq.
    table = data["channelData"]
    assert list(table.keys()) == sorted(
        table.keys(), key=lambda x: int(x), reverse=True
    )

    mocked: list[Event] | None = mocker.events.get("slac/slac_lsstcam")
    assert mocked
    mocked_table: dict[str, dict[str, dict]] = {}
    for event in mocked:
        seq_num = str(event.seq_num)
        if seq_num not in mocked_table:
            mocked_table[seq_num] = {}
        mocked_table[seq_num][event.channel_name] = event.__dict__

    for num, row in table.items():
        assert sorted(row) == sorted(mocked_table[num])
