"""Handlers for the app's api root, ``/rubintv/api/``."""
import asyncio
import base64
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from rubintv.background.bucketpoller import BucketPoller
from rubintv.background.historicaldata import HistoricalPoller
from rubintv.models.helpers import (
    date_str_to_date,
    find_first,
    objects_to_events,
)
from rubintv.models.models import (
    Camera,
    Event,
    EventImage,
    EventJSONDict,
    Location,
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
    response_model=EventJSONDict,
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

    Raises
    ------
    `HTTPException`
        In the event that historical data is still being processed and is not
        ready to be returned, a 421 (Locked resource) response code is raised.
    """
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    day = get_current_day_obs()
    md = None
    events: dict[str, list[Event]] = {}
    if camera.online:
        bucket_poller: BucketPoller = request.app.state.bucket_poller
        bucket: S3Client = request.app.state.s3_clients[location_name]
        objects = await bucket_poller.get_current_camera(
            location_name, camera_name
        )
        if objects:
            events_list = objects_to_events(objects)
            for e in events_list:
                if e.channel_name in events:
                    events[e.channel_name].append(e)
                else:
                    events[e.channel_name] = [e]

        md = bucket.get_object(f"{camera_name}/{day}/metadata.json")

        if not (events or md):
            historical: HistoricalPoller = request.app.state.historical
            if await historical.is_busy():
                raise HTTPException(421, "Historical data is being processed")
            day = await historical.get_most_recent_day(location, camera)
            events = await historical.get_events_for_date(
                location, camera, day
            )
            md = bucket.get_object(f"{camera_name}/{day}/metadata.json")

    return {
        "date": day,
        "channel_events": events,
        "metadata": md,
    }


@api_router.get(
    "/{location_name}/{camera_name}/date/{date_str}",
    response_model=dict[str, date | list[Event] | None | dict],
)
async def get_camera_events_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> dict[str, date | list[Event] | None | dict]:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    events = md = None
    if camera.online:
        historical: HistoricalPoller = request.app.state.historical
        bucket: S3Client = request.app.state.s3_clients[location_name]

        a_date = date_str_to_date(date_str)
        events = await historical.get_events_for_date(location, camera, a_date)
        md = bucket.get_object(f"{camera_name}/{date_str}/metadata.json")

    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")

    return {
        "date": day_obs,
        "channel_events": events,
        "metadata": md,
    }


@api_router.get(
    "/{location_name}/{camera_name}/{channel_name}/current",
    response_model=Event | None,
)
async def get_current_camera_channel_event(
    location_name: str, camera_name: str, channel_name: str, request: Request
) -> Event | None:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.channels:
        raise HTTPException(status_code=404, detail="Channel not found.")
    channel = find_first(camera.channels, "name", channel_name)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found.")
    event = None
    if camera.online:
        bucket_poller: BucketPoller = request.app.state.bucket_poller
        event = await bucket_poller.get_current_channel_event(
            location_name, camera_name, channel_name
        )
        if event is None:
            historical: HistoricalPoller = request.app.state.historical
            event = await historical.get_most_recent_event(
                location, camera, channel
            )
    return event


@api_router.get(
    "/{location_name}/{camera_name}/event",
    response_model=EventImage | None,
    name="api_event",
)
async def get_specific_channel_event(
    location_name: str,
    camera_name: str,
    key: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> EventImage | None:
    t = time.time()
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online or not key:
        return None
    bucket: S3Client = request.app.state.s3_clients[location_name]

    executor = ThreadPoolExecutor(max_workers=3)
    loop = asyncio.get_event_loop()
    object = await loop.run_in_executor(
        executor, bucket.get_binary_object, key
    )
    if not object:
        return None

    event = Event(key)
    if event.ext not in ["png", "jpg", "jpeg"]:
        return None
    image = base64.b64encode(object)
    event_image = EventImage(event, image)

    elapsed = time.time() - t
    logger.info(f"Time elapsed: {elapsed}")

    return event_image
