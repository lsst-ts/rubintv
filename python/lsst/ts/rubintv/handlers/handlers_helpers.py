"""Handlers for the app's api root, ``/rubintv/api/``."""
import asyncio
from datetime import date
from typing import Any, Callable

from fastapi import HTTPException, Request
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.models.models import (
    Camera,
    Location,
    NightReportPayload,
    get_current_day_obs,
)


async def get_camera_current_data(
    location: Location, camera: Camera, request: Request
) -> tuple[Any, Any, Any, Any, Any] | None:
    if not camera.online:
        return None
    current_poller: CurrentPoller = request.app.state.current_poller
    while not current_poller.completed_first_poll:
        await asyncio.sleep(0.3)

    day_obs = None
    channel_data = await current_poller.get_current_channel_table(location.name, camera)
    metadata = await current_poller.get_current_metadata(location.name, camera)
    per_day = await current_poller.get_current_per_day_data(location.name, camera)
    nr_exists = await current_poller.night_report_exists(location.name, camera.name)

    if not (per_day or metadata or channel_data):
        hist_data = await get_most_recent_historical_data(location, camera, request)
        if hist_data:
            (
                day_obs,
                channel_data,
                per_day,
                metadata,
                nr_exists,
            ) = hist_data
    else:
        day_obs = get_current_day_obs()
    return (day_obs, channel_data, per_day, metadata, nr_exists)


async def get_most_recent_historical_data(
    location: Location, camera: Camera, request: Request
) -> tuple[Any, Any, Any, Any, Any] | None:
    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")
    day_obs = await historical.get_most_recent_day(location, camera)
    if not day_obs:
        return None
    data = await get_camera_events_for_date(location, camera, day_obs, request)
    if not data:
        return None
    return (day_obs, *data)


async def get_camera_events_for_date(
    location: Location, camera: Camera, day_obs: date, request: Request
) -> tuple[Any, Any, Any, Any] | None:
    historical: HistoricalPoller = request.app.state.historical
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
    location: Location, camera: Camera, request: Request
) -> tuple[date, NightReportPayload]:
    day_obs = get_current_day_obs()
    current_poller: CurrentPoller = request.app.state.current_poller
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
