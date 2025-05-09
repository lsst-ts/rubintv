"""Handlers for the app's api root, ``/rubintv/api/``."""

from typing import Annotated

import redis.exceptions  # type: ignore
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.handlers_helpers import (
    date_validation,
    get_camera_events_for_date,
    get_current_night_report_payload,
)
from lsst.ts.rubintv.models.models import (
    Camera,
    CameraPageData,
    Event,
    KeyValue,
    Location,
    NightReport,
)
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.s3client import S3Client

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


@api_router.post("/redis")
async def redis_post(request: Request, message: KeyValue) -> dict:
    redis_client = request.app.state.redis_client
    if not redis_client:
        raise HTTPException(500, "Redis client not initialized")
    key, value = message.key, message.value
    if not key:
        raise HTTPException(400, "Message must contain a 'key' key")
    if key != "clear_redis" and value is None:
        raise HTTPException(400, "Message must contain a 'value' key")
    if key == "clear_redis":
        try:
            response = await redis_client.flushdb()
            logger.info("Redis database cleared")
        except Exception as e:
            logger.error(f"Failed to clear Redis database: {e}")
            raise HTTPException(500, f"Failed to clear Redis database: {e}")
        return {"response": response}
    else:
        logger.info("Setting Redis key", extra={"key": key, "value": value})
        try:
            response = await redis_client.set(key, value)
        except redis.exceptions.ResponseError:
            raise HTTPException(500, "Failed to set Redis key: No response")
        except redis.exceptions.TimeoutError:
            logger.error("Failed to set Redis key: Timeout")
            raise HTTPException(500, "Failed to set Redis key: Timeout")
        except redis.exceptions.ConnectionError:
            raise HTTPException(500, "Failed to set Redis key: Connection error")
        except redis.exceptions.RedisError as e:
            raise HTTPException(500, f"Failed to set Redis key: {e}")
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
    location, camera = await get_location_camera(location_name, camera_name, request)

    day_obs = date_validation(date_str)

    data: CameraPageData = await get_camera_events_for_date(
        location, camera, day_obs, request
    )
    if not data.is_empty():
        return {
            "date": day_obs,
            "channelData": data.channel_data,
            "metadata": data.metadata,
            "perDay": data.per_day,
            "nightReportExists": data.nr_exists,
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
                raise HTTPException(423, "Historical data is being processed")
            event = await historical.get_most_recent_event(location, camera, channel)
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
        Query(pattern=r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)(\.\w+)?$"),
    ],
    request: Request,
) -> Event | None:
    _, camera = await get_location_camera(location_name, camera_name, request)
    if not camera.online or not key:
        return None
    if not key.endswith(r"\.\w+"):
        # There is no file extension given, so we need to establish it
        # by looking it up in the bucket
        s3_client: S3Client = request.app.state.s3_clients[location_name]
        if not s3_client:
            raise HTTPException(status_code=404, detail="Location not found.")
        # Check if the key exists in the bucket
        objects = await s3_client.async_list_objects(key)
        if not objects:
            raise HTTPException(status_code=404, detail="Key not found.")
        # Get the first object that matches the key
        # and has a valid file extension
        for obj in objects:
            logger.info("Object found:", obj=obj)
            if obj["key"].startswith(key):
                key = obj["key"]
                break
        else:
            raise HTTPException(status_code=404, detail="Key not found.")
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


@api_router.get("/{location_name}/{camera_name}/metadata/{date_str}")
async def get_metadata_for_date(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> dict:

    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")

    location, camera = await get_location_camera(location_name, camera_name, request)
    if not camera.online:
        raise HTTPException(status_code=404, detail="Camera not found.")

    day_obs = date_validation(date_str)

    metadata = await historical.get_metadata_for_date(location, camera, day_obs)
    return metadata
