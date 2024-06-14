"""Handlers for the app's api root, ``/rubintv/api/``."""

import asyncio
from datetime import date
from typing import Any, Callable

import structlog
from fastapi import HTTPException, Request
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReport,
    get_current_day_obs,
)
from starlette.requests import HTTPConnection

logger = structlog.get_logger("rubintv")


async def get_camera_current_data(
    location: Location,
    camera: Camera,
    connection: HTTPConnection,
    use_historical: bool = True,
) -> tuple[None | date, dict, dict, dict, bool, bool] | None:
    if not camera.online:
        return None
    current_poller: CurrentPoller = connection.app.state.current_poller
    while not current_poller.completed_first_poll:
        await asyncio.sleep(0.3)

    day_obs = None
    is_historical = False
    channel_data = await current_poller.get_current_channel_table(location.name, camera)
    metadata = await current_poller.get_current_metadata(location.name, camera)
    per_day = await current_poller.get_current_per_day_data(location.name, camera)
    nr_exists = await current_poller.night_report_exists(location.name, camera.name)

    if not (per_day or metadata or channel_data) and use_historical:
        hist_data = await get_most_recent_historical_data(location, camera, connection)
        if hist_data:
            (
                day_obs,
                channel_data,
                per_day,
                metadata,
                nr_exists,
            ) = hist_data
            is_historical = True
    else:
        day_obs = get_current_day_obs()
    return (day_obs, channel_data, per_day, metadata, nr_exists, is_historical)


async def get_most_recent_historical_data(
    location: Location, camera: Camera, connection: HTTPConnection
) -> tuple[Any, Any, Any, Any, Any] | None:
    historical: HistoricalPoller = connection.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")
    day_obs = await historical.get_most_recent_day(location, camera)
    if not day_obs:
        return None
    data = await get_camera_events_for_date(location, camera, day_obs, connection)
    if not data:
        return None
    return (day_obs, *data)


async def get_camera_events_for_date(
    location: Location, camera: Camera, day_obs: date, connection: HTTPConnection
) -> tuple[Any, Any, Any, Any] | None:
    historical: HistoricalPoller = connection.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")
    channel_data = await historical.get_channel_data_for_date(location, camera, day_obs)
    metadata = await historical.get_metadata_for_date(location, camera, day_obs)
    per_day = await historical.get_per_day_for_date(location, camera, day_obs)
    nr_exists = await historical.night_report_exists_for(location, camera, day_obs)
    return (channel_data, per_day, metadata, nr_exists)


async def get_camera_calendar(
    location: Location, camera: Camera, request: Request
) -> dict[int, dict[int, dict[int, int]]]:
    historical: HistoricalPoller = request.app.state.historical
    return await historical.get_camera_calendar(location, camera)


async def get_current_night_report_payload(
    location: Location, camera: Camera, connection: HTTPConnection
) -> tuple[date, NightReport]:
    day_obs = get_current_day_obs()
    current_poller: CurrentPoller = connection.app.state.current_poller
    night_report = await current_poller.get_current_night_report(
        location.name, camera.name
    )
    return day_obs, night_report


async def try_historical_call(
    async_func: Callable, *args: Any, **kwargs: Any
) -> tuple[Any, bool]:
    try:
        result = await async_func(*args, **kwargs)
        return result, False
    except HTTPException as e:
        if e.status_code == 423:
            return None, True
        else:
            raise e


async def get_prev_next_event(
    location: Location, camera: Camera, event: Event, request: Request
) -> dict[str, dict | None]:
    nxt: dict | None = None
    prv: dict | None = None
    day_obs = event.day_obs_date()
    if day_obs == get_current_day_obs():
        cp: CurrentPoller = request.app.state.current_poller
        nxt, prv = await cp.get_next_prev_event(location.name, event)
    else:
        hp: HistoricalPoller = request.app.state.historical
        if await hp.is_busy():
            raise HTTPException(423, "Historical data is being processed")
        nxt, prv = await hp.get_next_prev_event(location, camera, event)
    return {"next": nxt, "prev": prv}
