"""Handlers for the app's api root, ``/rubintv/api/``."""
from datetime import date
from itertools import chain

from fastapi import APIRouter, HTTPException, Request

from rubintv.background.bucketpoller import BucketPoller, objects_to_events
from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Event, Location, get_current_day_obs

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
    response_model=Camera,
)
async def get_location_camera(
    location_name: str, camera_name: str, request: Request
) -> Camera:
    location = await get_location(location_name, request)
    cameras = request.app.state.models.cameras
    camera_groups = location.camera_groups.values()
    location_cams = chain(*camera_groups)
    if camera_name not in location_cams or not (
        camera := find_first(cameras, "name", camera_name)
    ):
        raise HTTPException(status_code=404, detail="Camera not found.")
    return camera


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
    location = await get_location(location_name, request)
    camera = await get_location_camera(location_name, camera_name, request)
    current_day_obs = get_current_day_obs()
    channel_events = md = None
    if camera.online:
        bucket_poller: BucketPoller = request.app.state.bucket_poller
        objects = await bucket_poller.get_current_state(
            location_name, camera_name
        )
        channel_events = objects_to_events(objects)

        md = bucket_poller.get_object(
            location.bucket_name,
            f"{camera_name}/{current_day_obs}/metadata.json",
        )

    return {
        "date": current_day_obs,
        "channel_events": channel_events,
        "metadata": md,
    }
