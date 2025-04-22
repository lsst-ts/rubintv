"""Handlers for the app's api root, ``/rubintv/api/``."""

import asyncio
from datetime import date
from typing import Any, Callable

import redis.asyncio as redis
from fastapi import HTTPException, Request
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReport,
    get_current_day_obs,
)
from lsst.ts.rubintv.models.models_helpers import date_str_to_date
from starlette.requests import HTTPConnection

logger = rubintv_logger()


async def get_camera_current_data(
    location: Location,
    camera: Camera,
    connection: HTTPConnection,
) -> tuple[dict, dict, dict, bool] | None:
    if not camera.online:
        return None
    current_poller: CurrentPoller = connection.app.state.current_poller
    while not current_poller.completed_first_poll:
        await asyncio.sleep(0.3)
    channel_data = await current_poller.get_current_channel_table(location.name, camera)
    metadata = await current_poller.get_current_metadata(location.name, camera)
    per_day = await current_poller.get_current_per_day_data(location.name, camera)
    nr_exists = current_poller.night_report_exists(location.name, camera.name)
    if not (channel_data or metadata or per_day or nr_exists):
        return None
    return (channel_data, per_day, metadata, nr_exists)


async def get_latest_metadata(
    location: Location,
    camera: Camera,
    connection: HTTPConnection,
) -> dict | None:
    if not camera.online:
        return None
    current_poller: CurrentPoller = connection.app.state.current_poller
    while not current_poller.completed_first_poll:
        await asyncio.sleep(0.3)
    metadata = await current_poller.get_latest_metadata(location.name, camera)
    if not metadata:
        return None
    return metadata


async def get_most_recent_historical_day(
    location: Location, camera: Camera, connection: HTTPConnection
) -> date | None:
    historical: HistoricalPoller = connection.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")
    day_obs = await historical.get_most_recent_day(location, camera)
    if not day_obs:
        return None
    data = await get_camera_events_for_date(location, camera, day_obs, connection)
    if not data:
        return None
    return day_obs


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
    if not (channel_data or metadata or per_day or nr_exists):
        return None
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
    async_func: Callable, is_busy_default: Any = None, *args: Any, **kwargs: Any
) -> tuple[Any, bool]:
    try:
        result = await async_func(*args, **kwargs)
        return result, False
    except HTTPException as e:
        if e.status_code == 423:
            return is_busy_default, True
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


def date_validation(date_str: str) -> date:
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")
    return day_obs


async def validate_redis_connection(app_state: Any) -> redis.Redis:
    try:
        redis_client: redis.Redis = app_state.redis_client
    except AttributeError:
        raise HTTPException(500, "Redis not connected")
    if not redis_client:
        raise HTTPException(500, "Redis not connected")
    ping = await redis_client.ping()
    if not ping:
        raise HTTPException(500, "Redis is unreachable")
    return redis_client
