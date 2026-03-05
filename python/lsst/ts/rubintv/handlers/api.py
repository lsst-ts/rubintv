"""Handlers for the app's api root, ``/rubintv/api/``."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.api_logic import (
    get_camera_date_data,
    get_current_channel_event_logic,
    get_current_night_report_logic,
    get_historical_metadata_logic,
    get_historical_night_report_logic,
    get_location_and_camera,
    get_redis_control_values_with_menus,
    get_specific_channel_event_logic,
    set_redis_value_logic,
)
from lsst.ts.rubintv.handlers.handlers_helpers import date_validation
from lsst.ts.rubintv.models.models import Camera, Event, KeyValue, Location, NightReport
from lsst.ts.rubintv.models.models_helpers import find_first
from redis.asyncio import Redis  # type: ignore

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
    await current.clear_todays_data()


@api_router.get("/redis/controlvalues")
async def redis_get(request: Request) -> list[KeyValue]:
    redis_client: Redis = request.app.state.redis_client
    if not redis_client:
        raise HTTPException(500, "Redis client not initialized")
    admin_redis_menus = request.app.state.models.admin_redis_menus
    return await get_redis_control_values_with_menus(redis_client, admin_redis_menus)


@api_router.post("/redis")
async def redis_post(request: Request, message: KeyValue) -> dict:
    redis_client: Redis = request.app.state.redis_client
    if not redis_client:
        raise HTTPException(500, "Redis client not initialized")
    key, value = message.key, message.value
    if not key:
        raise HTTPException(400, "Message must contain a 'key' key")
    response = await set_redis_value_logic(redis_client, key, value)
    return {"response": response}


@api_router.get("/slac", response_class=RedirectResponse)
async def redirect_slac_no_slash(request: Request) -> RedirectResponse:
    new_url = request.url.replace(path="/rubintv/usdf")
    return RedirectResponse(url=str(new_url), status_code=301)


@api_router.get("/slac/{path:path}", response_class=RedirectResponse)
async def redirect_slac(path: str | None, request: Request) -> RedirectResponse:
    old_path = request.url.path
    new_path = old_path.replace("/slac", "/usdf", 1)
    new_url = request.url.replace(path=new_path)
    return RedirectResponse(url=str(new_url), status_code=301)


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
    "/{location_name}/{camera_name}/date/{date_str}",
    response_model=dict,
)
async def get_camera_events_for_date_api(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> dict:
    location, camera = await get_location_and_camera(
        location_name, camera_name, request.app.state.models.locations
    )
    day_obs = date_validation(date_str)
    return await get_camera_date_data(location, camera, day_obs, request)


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

    return await get_current_channel_event_logic(location, camera, channel, request)


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
        Query(pattern=r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)(\.\w+)?$"),
    ],
    request: Request,
) -> Event | None:
    """Get a specific event from the camera.
    If the key has no file extension, it will be looked up in the bucket.

    Parameters
    ----------
    location_name : str
        Location name.
    camera_name : str
        Camera name.
    request : Request
        the request object.
    key : str
        Checked against a regex for valid key patterns, either the whole
        key or the key without the file extension.

    Returns
    -------
    Event | None
        The event object if found, None if not found or the camera is
        offline.

    Raises
    ------
    HTTPException
        404: If the location or camera is not found.
    """
    _, camera = await get_location_camera(location_name, camera_name, request)
    return await get_specific_channel_event_logic(location_name, key, camera, request)


@api_router.get(
    "/{location_name}/{camera_name}/night_report",
    response_model=dict,
)
async def get_current_night_report_api(
    location_name: str, camera_name: str, request: Request
) -> dict:
    location, camera = await get_location_camera(location_name, camera_name, request)
    return await get_current_night_report_logic(location, camera, request)


@api_router.get(
    "/{location_name}/{camera_name}/night_report/{date_str}",
    response_model=NightReport,
)
async def get_night_report_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> NightReport:
    location, camera = await get_location_camera(location_name, camera_name, request)
    day_obs = date_validation(date_str)
    return await get_historical_night_report_logic(location, camera, day_obs, request)


@api_router.get("/{location_name}/{camera_name}/metadata/{date_str}")
async def get_metadata_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> dict:
    location, camera = await get_location_camera(location_name, camera_name, request)
    day_obs = date_validation(date_str)
    return await get_historical_metadata_logic(location, camera, day_obs, request)
