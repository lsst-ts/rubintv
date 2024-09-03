"""Handlers for the app's api root, ``/rubintv/api/``."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.handlers_helpers import (
    date_validation,
    get_camera_current_data,
    get_camera_events_for_date,
    get_current_night_report_payload,
)
from lsst.ts.rubintv.models.models import Camera, Event, Location, NightReport
from lsst.ts.rubintv.models.models_helpers import find_first

api_router = APIRouter()
"""FastAPI router for all external handlers."""

logger = rubintv_logger()


@api_router.get("/", response_model=list[Location])
async def get_api_root(request: Request) -> list[Location]:
    locations = request.app.state.models.locations
    return locations


@api_router.post("/historical_reset")
async def historical_reset(request: Request) -> None:
    historical: HistoricalPoller = request.app.state.historical
    await historical.trigger_reload_everything()
    current: CurrentPoller = request.app.state.current_poller
    await current.clear_all_data()


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
    location, camera = await get_location_camera(location_name, camera_name, request)
    data = await get_camera_current_data(location, camera, request)
    if data:
        day_obs, channel_data, per_day, metadata, nr_exists, not_current = data
        return {
            "date": day_obs,
            "channelData": channel_data,
            "metadata": metadata,
            "perDay": per_day,
            "nightReportExists": nr_exists,
            "isHistorical": not_current,
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
    location, camera = await get_location_camera(location_name, camera_name, request)

    day_obs = date_validation(date_str)

    data = await get_camera_events_for_date(location, camera, day_obs, request)
    if data:
        channel_data, per_day, metadata, nr_exists = data
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
    location, camera = await get_location_camera(location_name, camera_name, request)
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
            event = await historical.get_most_recent_event(location, camera, channel)
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
        Query(pattern=r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)\.(\w+)$"),
    ],
    request: Request,
) -> Event | None:
    location, camera = await get_location_camera(location_name, camera_name, request)
    if not camera.online or not key:
        return None

    event = Event(key=key)
    if event.ext not in ["png", "jpg", "jpeg", "mp4"]:
        return None
    return event


@api_router.get(
    "/{location_name}/{camera_name}/night_report",
    response_model=dict,
)
async def get_current_night_report_api(
    location_name: str, camera_name: str, request: Request
) -> dict:
    location, camera = await get_location_camera(location_name, camera_name, request)
    day_obs, nr = await get_current_night_report_payload(location, camera, request)
    return {"date": day_obs, "night_report": nr}


@api_router.get(
    "/{location_name}/{camera_name}/night_report/{date_str}",
    response_model=NightReport,
)
async def get_night_report_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> NightReport:
    location, camera = await get_location_camera(location_name, camera_name, request)

    day_obs = date_validation(date_str)

    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")

    nr = await historical.get_night_report_payload(location, camera, day_obs)
    return nr
