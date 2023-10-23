"""Handlers for the app's api root, ``/rubintv/api/``."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from rubintv.background.currentpoller import CurrentPoller
from rubintv.background.historicaldata import HistoricalPoller
from rubintv.handlers.handlers_helpers import (
    get_camera_current_data,
    get_camera_events_for_date,
)
from rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReportDataDict,
    get_current_day_obs,
)
from rubintv.models.models_helpers import date_str_to_date, find_first

__all__ = [
    "api_router",
    "get_location",
    "get_location_camera",
    "get_camera_current_events_api",
]

api_router = APIRouter()
"""FastAPI router for all external handlers."""


@api_router.get("/", response_model=list[Location])
async def get_api_root(request: Request) -> list[Location]:
    locations = request.app.state.models.locations
    return locations


@api_router.get("/{location_name}", response_model=Location)
async def get_location(location_name: str, request: Request) -> Location:
    locations = request.app.state.models.locations
    if not (location := find_first(locations, "name", location_name)):
        raise HTTPException(status_code=404, detail="Location not found.")
    return location


@api_router.get(
    "/{location_name}/{camera_name}",
    response_model=tuple[Location, Camera],
)
async def get_location_camera(
    location_name: str, camera_name: str, request: Request
) -> tuple[Location, Camera]:
    location = await get_location(location_name, request)
    cameras = location.cameras
    if not (camera := find_first(cameras, "name", camera_name)):
        raise HTTPException(status_code=404, detail="Camera not found.")
    return (location, camera)


@api_router.get(
    "/{location_name}/{camera_name}/current",
    response_model=dict,
)
async def get_camera_current_events_api(
    location_name: str, camera_name: str, request: Request
) -> dict:
    """Returns current channel and meta-data from the requested camera.

    The function looks for results from today first. If it finds none from
    today, it looks for the most recent results from the historical data.

    Parameters
    ----------
    location_name : `str`
        The name of the camera location.
    camera_name : `str`
        The name of the camera.
    request : `Request`
        The http request object.

    Returns
    -------
    response: `dict`
        The returning dict contains the current day obs date and either a list
        of events or none if there are no channel events and a dict which
        contains any current metadata for the given camera.

    """
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    data = await get_camera_current_data(location, camera, request)
    if data:
        day_obs, channel_data, per_day, metadata, nr_exists, events = data
        return {
            "date": day_obs,
            "channelData": channel_data,
            "metadata": metadata,
            "perDay": per_day,
            "nightReportExists": nr_exists,
        }
    else:
        return {}


@api_router.get(
    "/{location_name}/{camera_name}/date/{date_str}",
    response_model=dict,
)
async def get_camera_events_for_date_api(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> dict:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")
    data = await get_camera_events_for_date(location, camera, day_obs, request)
    if data:
        channel_data, per_day, metadata, nr_exists, events = data
        return {
            "date": day_obs,
            "channelData": channel_data,
            "metadata": metadata,
            "perDay": per_day,
            "nightReportExists": nr_exists,
        }
    else:
        return {}


@api_router.get(
    "/{location_name}/{camera_name}/{channel_name}/current",
    response_model=Event | None,
)
async def get_current_channel_event(
    location_name: str, camera_name: str, channel_name: str, request: Request
) -> Event | None:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.channels or not (
        channel := find_first(camera.channels, "name", channel_name)
    ):
        raise HTTPException(status_code=404, detail="Channel not found.")

    event = None
    if camera.online:
        current_poller: CurrentPoller = request.app.state.current_poller
        event = await current_poller.get_current_channel_event(
            location_name, camera_name, channel_name
        )
        if not event:
            historical: HistoricalPoller = request.app.state.historical
            if await historical.is_busy():
                raise HTTPException(421, "Historical data is being processed")
            event = await historical.get_most_recent_event(
                location, camera, channel
            )
            if not event:
                return None
    return event


@api_router.get(
    "/{location_name}/{camera_name}/event",
    response_model=Event | None,
    name="api_event",
)
async def get_specific_channel_event(
    location_name: str,
    camera_name: str,
    key: Annotated[
        str,
        Query(
            pattern=r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)\.(\w+)$"
        ),
    ],
    request: Request,
) -> Event | None:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online or not key:
        return None

    event = Event(key)
    if event.ext not in ["png", "jpg", "jpeg", "mp4"]:
        return None
    return event


@api_router.get(
    "/{location_name}/{camera_name}/night_report",
    response_model=dict,
)
async def get_current_night_report(
    location_name: str, camera_name: str, request: Request
) -> NightReportDataDict:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    day_obs = get_current_day_obs()
    current_poller: CurrentPoller = request.app.state.current_poller
    nr = await current_poller.get_current_night_report(
        location_name, camera_name
    )
    return {"date": day_obs, "night_report": nr}


@api_router.get(
    "/{location_name}/{camera_name}/night_report/{date_str}",
    response_model=dict,
)
async def get_night_report_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> NightReportDataDict:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")

    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")

    nr = await historical.get_night_report(location, camera, day_obs)
    return {"date": day_obs, "night_report": nr}


async def get_calendar_of_historical_events(
    location: Location, camera: Camera, request: Request
) -> dict[int, dict[int, dict[int, int]]]:
    historical: HistoricalPoller = request.app.state.historical
    events_calendar = await historical.get_camera_calendar(location, camera)
    return events_calendar


async def current_night_report_exists(
    location: Location, camera: Camera, request: Request
) -> bool:
    cp: CurrentPoller = request.app.state.current_poller
    return await cp.night_report_exists(location.name, camera.name)


async def night_report_exists_for(
    location: Location, camera: Camera, day_obs: date, request: Request
) -> bool:
    historical: HistoricalPoller = request.app.state.historical
    return await historical.night_report_exists_for(location, camera, day_obs)
