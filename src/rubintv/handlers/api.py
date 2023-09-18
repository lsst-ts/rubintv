"""Handlers for the app's api root, ``/rubintv/api/``."""
from datetime import date

from fastapi import APIRouter, HTTPException, Request

from rubintv.background.bucketpoller import BucketPoller
from rubintv.background.historicaldata import HistoricalPoller
from rubintv.models.helpers import (
    date_str_to_date,
    find_first,
    objects_to_events,
)
from rubintv.models.models import Camera, Event, Location, get_current_day_obs
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
    response_model=dict[str, date | list[Event] | None | dict],
)
async def get_camera_current_events(
    location_name: str, camera_name: str, request: Request
) -> dict[str, date | list[Event] | None | dict]:
    """Returns current channel and meta-data from the requested camera.

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
    response: `dict` [`str`, `date` | `list` [`Event`] | `None`]
        The returning dict contains the current day obs date and either a list
        of events or none if there are no channel events and a dict which
        contains any current metadata for the given camera.
    """
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    current_day_obs = get_current_day_obs()
    channel_events = md = None
    if camera.online:
        bucket_poller: BucketPoller = request.app.state.bucket_poller
        bucket: S3Client = request.app.state.s3_clients[location_name]
        objects = await bucket_poller.get_current_camera(
            location_name, camera_name
        )
        channel_events = None
        if objects:
            channel_events = objects_to_events(objects)

        md = bucket.get_object(
            f"{camera_name}/{current_day_obs}/metadata.json"
        )
        # md = bucket.list_objects(f"{camera_name}/2023-09-14/stills")

    return {
        "date": current_day_obs,
        "channel_events": channel_events,
        "metadata": md,
    }


@api_router.get(
    "/{location_name}/{camera_name}/{date_str}",
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

        events = historical.get_events_for_date(location, camera, date_str)
        md = bucket.get_object(f"{camera_name}/{date_str}/metadata.json")

    day_obs = date_str_to_date(date_str)

    return {
        "date": day_obs,
        "channel_events": events,
        "metadata": md,
    }
