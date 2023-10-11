"""Handlers for the app's api root, ``/rubintv/api/``."""
import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from rubintv.background.currentpoller import CurrentPoller
from rubintv.background.historicaldata import HistoricalPoller
from rubintv.models.helpers import (
    date_str_to_date,
    find_first,
    objects_to_events,
)
from rubintv.models.models import (
    Camera,
    Event,
    EventJSONDict,
    Location,
    NightReportDataDict,
    get_current_day_obs,
)
from rubintv.s3client import S3Client

__all__ = [
    "api_router",
    "get_location",
    "get_location_camera",
    "get_camera_current_events",
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
async def get_camera_current_events(
    location_name: str, camera_name: str, request: Request
) -> EventJSONDict:
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
    response: `EventJSONDict`
        The returning dict contains the current day obs date and either a list
        of events or none if there are no channel events and a dict which
        contains any current metadata for the given camera.

    """
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    day = get_current_day_obs()
    md = None
    events: dict[str, list[Event]] = {}
    if camera.online:
        current_poller: CurrentPoller = request.app.state.current_poller

        if not current_poller.completed_first_poll:
            for r in range(1, 3):
                objects = await current_poller.get_current_objects(
                    location_name, camera_name
                )
                if not objects:
                    print("Retrying...")
                    await asyncio.sleep(0.3)

        objects = await current_poller.get_current_objects(
            location_name, camera_name
        )
        if objects:
            events_list = objects_to_events(objects)
            for e in events_list:
                if e.channel_name in events:
                    events[e.channel_name].append(e)
                else:
                    events[e.channel_name] = [e]

        md = await current_poller.get_current_metadata(location_name, camera)

        if not (events and md):
            h_data = await get_most_recent_historical_data(
                location, camera, request
            )
            if h_data:
                day, events, md = h_data

    return {
        "date": day,
        "channel_events": events,
        "metadata": md,
    }


async def get_most_recent_historical_data(
    location: Location, camera: Camera, request: Request
) -> tuple[date, dict[str, list[Event]], dict | None] | None:
    """_summary_

    Parameters
    ----------
    location : Location
        _description_
    camera : Camera
        _description_
    request : Request
        _description_

    Returns
    -------
    tuple[date, dict[str, Event], dict | None]
        _description_

    Raises
    ------
    `HTTPException`
        In the event that historical data is still being processed and is not
        ready to be returned, a 421 (Locked resource) response code is raised.
    """
    bucket: S3Client = request.app.state.s3_clients[location.name]
    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")

    day = await historical.get_most_recent_day(location, camera)
    if not day:
        return None
    events = await historical.get_event_dict_for_date(location, camera, day)
    md = await bucket.async_get_object(f"{camera.name}/{day}/metadata.json")
    return (day, events, md)


@api_router.get(
    "/{location_name}/{camera_name}/date/{date_str}",
    response_model=dict,
)
async def get_camera_events_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> EventJSONDict:
    today_str = get_current_day_obs().isoformat()
    if date_str == today_str:
        return await get_camera_current_events(
            location_name, camera_name, request
        )

    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")

    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    events: dict[str, list[Event]] = {}
    md = None
    if camera.online:
        historical: HistoricalPoller = request.app.state.historical
        if await historical.is_busy():
            raise HTTPException(423, "Historical data is being processed")

        bucket: S3Client = request.app.state.s3_clients[location_name]

        events = await historical.get_event_dict_for_date(
            location, camera, day_obs
        )
        md = await bucket.async_get_object(
            f"{camera_name}/{date_str}/metadata.json"
        )

    return {
        "date": day_obs,
        "channel_events": events,
        "metadata": md,
    }


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
        s3_client: S3Client = request.app.state.s3_clients[location_name]
        event.url = await s3_client.get_presigned_url(event.key)
        if not event.url:
            raise HTTPException(status_code=404, detail="Key not found.")
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

    s3_client: S3Client = request.app.state.s3_clients[location_name]
    event.url = await s3_client.get_presigned_url(key)
    if not event.url:
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
    return await cp.current_night_report_exists(location.name, camera.name)


async def night_report_exists_for(
    location: Location, camera: Camera, day_obs: date, request: Request
) -> bool:
    historical: HistoricalPoller = request.app.state.historical
    return await historical.night_report_exists_for(location, camera, day_obs)
