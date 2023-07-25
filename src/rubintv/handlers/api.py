"""Handlers for the app's external root, ``/rubintv/``."""
from datetime import date
from itertools import chain
from typing import Tuple

from fastapi import APIRouter, HTTPException, Request

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Event, Location, get_current_day_obs

__all__ = ["api_router"]

api_router = APIRouter()
"""FastAPI router for all external handlers."""


@api_router.get("/location/{location_name}", response_model=Location)
async def get_location(
    location_name: str,
    request: Request,
) -> Location:
    locations = request.app.state.fixtures.locations
    if not (location := find_first(locations, "name", location_name)):
        raise HTTPException(status_code=404, detail="Location not found.")
    return location


@api_router.get(
    "/location/{location_name}/camera/{camera_name}",
    response_model=Tuple[Location, Camera],
)
async def get_location_camera(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Tuple[Location, Camera]:
    location = await get_location(location_name, request)
    cameras = request.app.state.fixtures.cameras
    camera_groups = location.camera_groups.values()
    location_cams = chain(*camera_groups)
    if camera_name not in location_cams or not (
        camera := find_first(cameras, "name", camera_name)
    ):
        raise HTTPException(status_code=404, detail="Camera not found.")
    return (location, camera)


@api_router.get(
    "/location/{location_name}/camera/{camera_name}/current",
    response_model=Tuple[date, list[Event] | None],
)
async def get_camera_current_events(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Tuple[date, list[Event] | None]:
    await get_location_camera(location_name, camera_name, request)
    current_day_obs = get_current_day_obs()
    bucket_poller = request.app.state.bucket_poller
    events = await bucket_poller.get_current_state(location_name, camera_name)
    return (current_day_obs, events)
