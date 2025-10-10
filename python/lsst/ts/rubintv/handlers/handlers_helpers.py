"""Handlers for the app's api root, ``/rubintv/api/``."""

import asyncio
from datetime import date
from typing import Any, Callable

from fastapi import HTTPException, Request
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import (
    Camera,
    CurrentPageData,
    Event,
    HistoricalPageData,
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
) -> CurrentPageData:
    """Get the current data for a camera."""
    if not camera.online:
        return CurrentPageData()
    current_poller: CurrentPoller = connection.app.state.current_poller
    first_pass: asyncio.Event = connection.app.state.first_pass_event
    # wait for the first poll to complete
    await first_pass.wait()

    channel_data = await current_poller.get_current_channel_table(location.name, camera)
    metadata = await current_poller.get_current_metadata(location.name, camera)
    per_day = await current_poller.get_current_per_day_data(location.name, camera)
    nr_exists = current_poller.night_report_exists(location.name, camera.name)

    return CurrentPageData(
        channel_data=channel_data,
        per_day=per_day,
        metadata=metadata,
        nr_exists=nr_exists,
    )


async def get_latest_metadata(
    location: Location,
    camera: Camera,
    connection: HTTPConnection,
) -> dict | None:
    """Get the latest metadata for a camera."""
    if not camera.online:
        return None
    current_poller: CurrentPoller = connection.app.state.current_poller
    first_pass: asyncio.Event = connection.app.state.first_pass_event
    # wait for the first poll to complete
    await first_pass.wait()

    metadata = await current_poller.get_latest_metadata(location.name, camera)
    if not metadata:
        return None
    return metadata


async def get_most_recent_historical_day(
    location: Location, camera: Camera, connection: HTTPConnection
) -> date | None:
    """Get the most recent historical day for a camera."""
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
) -> HistoricalPageData:
    """Get the camera events for a particular date."""
    historical: HistoricalPoller = connection.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")
    structured_data = await historical.get_structured_data_for_date(
        location, camera, day_obs
    )
    extension_info = await historical.get_all_extensions_for_date(
        location, camera, day_obs
    )
    metadata_exists = await historical.check_for_metadata_for_date(
        location, camera, day_obs
    )
    per_day = await historical.get_per_day_for_date(location, camera, day_obs)
    nr_exists = await historical.night_report_exists_for(location, camera, day_obs)

    return HistoricalPageData(
        structured_data=structured_data,
        extension_info=extension_info,
        per_day=per_day,
        metadata_exists=metadata_exists,
        nr_exists=nr_exists,
    )


async def get_camera_calendar(
    location: Location, camera: Camera, request: Request
) -> dict[int, dict[int, dict[int, int]]]:
    """Get the camera calendar data for a particular date."""
    historical: HistoricalPoller = request.app.state.historical
    return await historical.get_camera_calendar(location, camera)


async def get_current_night_report_payload(
    location: Location, camera: Camera, connection: HTTPConnection
) -> tuple[date, NightReport]:
    """Get the current night report data for a camera."""
    day_obs = get_current_day_obs()
    current_poller: CurrentPoller = connection.app.state.current_poller
    night_report = await current_poller.get_current_night_report(
        location.name, camera.name
    )
    return day_obs, night_report


async def try_historical_call(
    async_func: Callable, is_busy_default: Any = None, *args: Any, **kwargs: Any
) -> tuple[Any, bool]:
    """Try to call a historical function and return the result.
    If the function raises an HTTPException with status code 423, return
    the default value and True to show the historical poller is busy.
    """
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
    """Get the previous and next events for a given event."""
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
    """Validate the date string and return a date object."""
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")
    return day_obs


async def get_all_channel_names_for_date_seq_num(
    location: Location,
    camera: Camera,
    day_obs: date,
    seq_num: int | str,
    connection: HTTPConnection,
) -> list[str]:
    """Get all channels for a given date and sequence number."""
    if day_obs == get_current_day_obs().isoformat():
        cp: CurrentPoller = connection.app.state.current_poller
        channel_data = await cp.get_all_channel_names_for_seq_num(
            location.name, camera.name, seq_num
        )
        return channel_data
    historical: HistoricalPoller = connection.app.state.historical
    channel_data, _ = await try_historical_call(
        historical.get_all_channel_names_for_date_and_seq_num,
        [],
        location,
        camera,
        day_obs,
        seq_num,
    )
    return channel_data
