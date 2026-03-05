"""Business logic for API endpoints.

This module contains the core logic for API operations, separate from the
HTTP endpoint handlers. This allows the logic to be reused across multiple
endpoints (old API, new API, pages, etc.) without duplication.
"""

from datetime import date
from typing import TYPE_CHECKING

import redis.exceptions
from fastapi import HTTPException
from lsst.ts.rubintv.background.currentpoller import CurrentPoller
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import REDIS_CONTROL_READBACK_SUFFIX as RC_SUFFIX
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.handlers_helpers import get_camera_events_for_date
from lsst.ts.rubintv.models.models import (
    Camera,
    CameraPageData,
    Channel,
    Event,
    KeyValue,
    Location,
    NightReport,
)
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.s3client import S3Client
from redis.asyncio import Redis

if TYPE_CHECKING:
    from fastapi import Request

logger = rubintv_logger()


async def get_location_and_camera(
    location_name: str, camera_name: str, locations: list[Location]
) -> tuple[Location, Camera]:
    """Get location and camera objects by name."""
    location = find_first(locations, "name", location_name)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found.")

    camera = find_first(location.cameras, "name", camera_name)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    return location, camera


async def get_camera_date_data(
    location: Location,
    camera: Camera,
    day_obs: date,
    request: "Request",
) -> dict:
    """Get camera data for a specific date (the core frontend API call)."""
    data: CameraPageData = await get_camera_events_for_date(
        location, camera, day_obs, request
    )

    if not data.is_empty():
        return {
            "date": day_obs,
            "structuredData": data.structured_data,
            "extensionInfo": data.extension_info,
            "metadata": data.metadata,
            "perDay": data.per_day,
            "nightReportExists": data.nr_exists,
        }
    else:
        return {}


async def get_current_channel_event_logic(
    location: Location,
    camera: Camera,
    channel: Channel,
    request: "Request",
) -> Event | None:
    """Get the current event for a specific channel."""
    event = None
    if camera.online:
        current_poller: CurrentPoller = request.app.state.current_poller
        event = await current_poller.get_current_channel_event(
            location.name, camera.name, channel.name
        )
        if not event:
            historical: HistoricalPoller = request.app.state.historical
            if await historical.is_busy():
                raise HTTPException(423, "Historical data is being processed")
            event = await historical.get_most_recent_event(location, camera, channel)
    return event


async def get_specific_channel_event_logic(
    location_name: str,
    key: str,
    camera: Camera,
    request: "Request",
) -> Event | None:
    """Get a specific event by key."""
    allowed_extensions = ["png", "jpg", "jpeg", "mp4"]

    if not camera.online or not key:
        return None

    has_ext = any(key.endswith(f".{ext}") for ext in allowed_extensions)
    if not has_ext:
        # No file extension given, look it up in bucket
        s3_client: S3Client = request.app.state.s3_clients[location_name]
        if not s3_client:
            raise HTTPException(status_code=404, detail="Location not found.")

        objects = await s3_client.async_list_objects(key)
        if not objects:
            raise HTTPException(status_code=404, detail="Key not found.")

        for obj in objects:
            if obj["key"].startswith(key):
                key = obj["key"]
                break
        else:
            raise HTTPException(status_code=404, detail="Key not found.")

    event = Event(key=key)
    if event.ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, detail=f"Invalid file extension: {event.ext}"
        )
    return event


async def get_current_night_report_logic(
    location: Location, camera: Camera, request: "Request"
) -> dict:
    """Get the current night report for a camera."""
    from lsst.ts.rubintv.handlers.handlers_helpers import (
        get_current_night_report_payload,
    )

    day_obs, nr = await get_current_night_report_payload(location, camera, request)
    return {"date": day_obs, "night_report": nr}


async def get_historical_night_report_logic(
    location: Location, camera: Camera, day_obs: date, request: "Request"
) -> NightReport:
    """Get the night report for a specific date."""
    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(423, "Historical data is being processed")

    nr = await historical.get_night_report_payload(location, camera, day_obs)
    return nr


async def get_historical_metadata_logic(
    location: Location, camera: Camera, day_obs: date, request: "Request"
) -> dict:
    """Get metadata for a specific date."""
    if not camera.online:
        raise HTTPException(status_code=404, detail="Camera not found.")

    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(
            status_code=423, detail="Historical data is being processed"
        )

    metadata = await historical.get_metadata_for_date(location, camera, day_obs)
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found for this date")

    return metadata


async def get_redis_control_values_with_menus(
    redis_client: Redis, admin_redis_menus: list[dict]
) -> list[KeyValue]:
    """Get all Redis control readback values using provided menu config."""
    if not redis_client:
        raise HTTPException(500, "Redis client not initialized")

    results = []
    try:
        for menu in admin_redis_menus:
            key = menu["key"] + RC_SUFFIX
            value = await redis_client.get(key)
            if value:
                value = value.decode("utf-8")
            else:
                value = ""
            results.append({"key": key, "value": value})
    except redis.exceptions.ResponseError:
        raise HTTPException(500, "Failed to get Redis key: No response")
    except redis.exceptions.TimeoutError:
        raise HTTPException(500, "Failed to get Redis key: Timeout")
    except redis.exceptions.ConnectionError:
        raise HTTPException(500, "Failed to get Redis key: Connection error")
    except redis.exceptions.RedisError as e:
        raise HTTPException(500, f"Failed to get Redis key: {e}")

    logger.info("Fetched Redis control values", extra={"results": results})
    return results


async def set_redis_value_logic(
    redis_client: Redis, key: str, value: str | int | float | bool | None
) -> bool | None:
    """Set a Redis key-value pair or clear the database."""
    if not redis_client:
        raise HTTPException(500, "Redis client not initialized")

    if not key:
        raise HTTPException(400, "Message must contain a 'key' key")

    response: bool | None = None
    if key == "clear_redis":
        try:
            response = await redis_client.flushdb()
            logger.info("Redis database cleared")
            return response
        except Exception as e:
            raise HTTPException(500, f"Failed to clear Redis database: {e}")
    else:
        logger.info("Setting Redis key", extra={"key": key, "value": value})
        if value is None:
            raise HTTPException(400, "Message must contain a 'value' key")
        try:
            response = await redis_client.set(key, value)
            return response
        except redis.exceptions.ResponseError:
            raise HTTPException(500, "Failed to set Redis key: No response")
        except redis.exceptions.TimeoutError:
            raise HTTPException(500, "Failed to set Redis key: Timeout")
        except redis.exceptions.ConnectionError:
            raise HTTPException(500, "Failed to set Redis key: Connection error")
        except redis.exceptions.RedisError as e:
            raise HTTPException(500, f"Failed to set Redis key: {e}")
