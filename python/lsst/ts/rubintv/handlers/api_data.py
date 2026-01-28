"""Generic data endpoint for the React SPA frontend.

This module provides a flexible `/api/data` endpoint that serves only the
core data collections needed by the frontend:
- sites: Get all observatory sites
- cameras: Get cameras for a site
- camera_data: Get full camera page data with calendar and metadata
- night_report: Get night report for a date
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from lsst.ts.rubintv.background.historicaldata import HistoricalPoller
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.handlers_helpers import (
    date_validation,
    get_camera_calendar,
    get_camera_current_data,
    get_camera_events_for_date_data_api,
    get_most_recent_historical_day,
)
from lsst.ts.rubintv.models.models import (
    CameraPageData,
    DataResponse,
    Location,
    get_current_day_obs,
)
from lsst.ts.rubintv.models.models_helpers import find_first

api_data_router = APIRouter()
"""FastAPI router for generic data endpoint."""

logger = rubintv_logger()


@api_data_router.get("/data")
async def get_data(
    request: Request,
    type: str = Query(
        ...,
        description="Data type to retrieve (sites, cameras, camera_data, night_report)",
    ),
    site: str | None = Query(None, description="Site/location name"),
    location: str | None = Query(None, description="[Deprecated] Use 'site' instead"),
    camera: str | None = None,
    date: str | None = None,
) -> DataResponse:
    """Generic data endpoint for React SPA frontend.

    Supports querying core data collections with flexible filtering.
    All responses use the standard DataResponse envelope format.

    Query types:
    - sites: Get all sites/locations
    - cameras: Get cameras for a site
    - camera_data: Get full camera page data (current or historical)
    - night_report: Get night report for a date

    Parameters
    ----------
    type : `str`
        The type of data to retrieve (sites, cameras, camera_data,
        night_report)
    site : `str` | `None`
        Site/location name (backwards compat: location)
    location : `str` | `None`
        [Deprecated] Use site parameter instead
    camera : `str` | `None`
        Camera name (required for cameras, camera_data, night_report)
    date : `str` | `None`
        Date in ISO format YYYY-MM-DD (optional for camera_data, required for
        night_report)

    Returns
    -------
    data_response: `DataResponse`
        Standard response envelope with data, status, metadata
    """
    # Handle backwards compatibility: location -> site
    resolved_site = site or location
    type_lower = type.lower()

    # Record query parameters for response metadata
    query_params = {
        "type": type,
        "site": resolved_site,
        "camera": camera,
        "date": date,
    }

    try:
        # Route to appropriate handler based on type
        data: Any
        if type_lower in ("sites", "locations"):
            data = await _handle_sites(request)
        elif type_lower == "cameras":
            data = await _handle_cameras(request, resolved_site)
        elif type_lower == "camera_data":
            data = await _handle_camera_data(request, resolved_site, camera, date)
        elif type_lower == "night_report":
            data = await _handle_night_report(request, resolved_site, camera, date)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown data type: {type}. "
                "Supported types: sites, cameras, camera_data, night_report",
            )

        return DataResponse(
            status="success",
            data=data,
            meta={
                "timestamp": datetime.now(
                    datetime.now().astimezone().tzinfo
                ).isoformat(),
                "queryType": type_lower,
                "queryParams": query_params,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in generic data endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Handler functions


async def _handle_sites(request: Request) -> list[Location]:
    """Handle sites/locations query type.

    Returns all observatory sites/locations.

    Returns
    -------
    locations: `list` [`Location`]
        List of all Location objects
    """
    locations: list[Location] = request.app.state.models.locations
    return locations


async def _handle_cameras(request: Request, site: str | None) -> dict[str, Any]:
    """Handle cameras query type.

    Returns all cameras for a given site.

    Parameters
    ----------
    request : `Request`
        FastAPI request object
    site : `str` | `None`
        Site/location name

    Returns
    -------
    cameras: `dict`[ `str`, `Any`]
        Dictionary with "cameras" key containing list of Camera objects

    Raises
    ------
    `HTTPException`
        If site is missing or not found
    """
    if not site:
        raise HTTPException(
            status_code=400, detail="'site' parameter is required for cameras query"
        )

    locations: list[Location] = request.app.state.models.locations
    location = find_first(locations, "name", site)
    if not location:
        raise HTTPException(status_code=404, detail=f"Site '{site}' not found")

    return {"cameras": location.cameras}


async def _handle_camera_data(
    request: Request,
    site: str | None,
    camera: str | None,
    date: str | None,
) -> dict[str, Any]:
    """Handle camera_data query type.

    Returns combined camera page data including structured
    data, metadata, calendar availability, and per_day
    information. Supports both current and historical data.

    Parameters
    ----------
    request : `Request`
        FastAPI request object
    site : `str` | `None`
        Site/location name
    camera : `str` | `None`
        Camera name
    date : `str` | `None`
        Date in ISO format (optional, defaults to current day)

    Returns
    -------
    reposonse: dict[`str`, `Any`]
        Combined response with:
        - date: ISO format date string
        - structuredData, extensionInfo, metadata: for tables
        - perDay: dict with per-day data
        - isCurrent: bool indicating if this is current day data
        - isHistorical: bool indicating if this is historical data
        - nrExists: bool indicating if night report exists
        - calendar: dict with calendar availability

    Raises
    ------
    `HTTPException`
        If required parameters are missing or not found
    """
    if not site or not camera:
        raise HTTPException(
            status_code=400,
            detail="'site' and 'camera' parameters are required for camera_data query",
        )

    locations: list[Location] = request.app.state.models.locations
    location = find_first(locations, "name", site)
    if not location:
        raise HTTPException(status_code=404, detail=f"Site '{site}' not found")

    cameras = location.cameras
    cam = find_first(cameras, "name", camera)
    if not cam:
        raise HTTPException(
            status_code=404, detail=f"Camera '{camera}' not found in site '{site}'"
        )

    if not cam.online:
        raise HTTPException(status_code=404, detail="Camera not online")

    # Determine the date to use
    if date:
        day_obs = date_validation(date)
    else:
        day_obs = get_current_day_obs()

    is_current = False
    is_historical = False

    data_obj: CameraPageData = CameraPageData()

    # Try to get current data if querying today
    current_day_obs = get_current_day_obs()
    if day_obs == current_day_obs:
        is_current = True
        data_obj = await get_camera_current_data(location, cam, request)

    # If current data is empty, try historical
    if data_obj.is_empty():
        is_current = False
        most_recent = await get_most_recent_historical_day(location, cam, request)
        if most_recent:
            day_obs = most_recent
            data_obj = await get_camera_events_for_date_data_api(
                location, cam, day_obs, request
            )
            is_historical = True

    # Get calendar data for the month
    calendar: dict[int, dict[int, dict[int, int]]] = {}
    if is_historical or data_obj.is_empty():
        # Only fetch calendar for historical views
        calendar = await get_camera_calendar(location, cam, request)

    # Build combined response
    response: dict[str, Any] = {
        "date": day_obs.isoformat() if day_obs else None,
        "perDay": data_obj.per_day,
        "structuredData": data_obj.structured_data,
        "extensionInfo": data_obj.extension_info,
        "metadata": data_obj.metadata,
        "isCurrent": is_current,
        "isHistorical": is_historical,
        "nrExists": data_obj.nr_exists,
        "calendar": calendar,
    }

    return response


async def _handle_night_report(
    request: Request,
    site: str | None,
    camera: str | None,
    date: str | None,
) -> dict[str, Any]:
    """Handle night_report query type.

    Returns night report data for a given date.

    Parameters
    ----------
    request : `Request`
        FastAPI request object
    site : `str` | `None`
        Site/location name
    camera : `str` | `None`
        Camera name
    date : `str` | `None`
        Date in ISO format

    Returns
    -------
    night_report: `dict`[`str`, `Any`]
        Dictionary with "nightReport" key containing NightReport data

    Raises
    ------
    `HTTPException`
        If required parameters are missing, not found, or historical data is
        busy
    """
    if not site or not camera or not date:
        raise HTTPException(
            status_code=400,
            detail="'site', 'camera', and 'date' parameters are required for night_report query",
        )

    locations: list[Location] = request.app.state.models.locations
    location = find_first(locations, "name", site)
    if not location:
        raise HTTPException(status_code=404, detail=f"Site '{site}' not found")

    cameras = location.cameras
    cam = find_first(cameras, "name", camera)
    if not cam:
        raise HTTPException(
            status_code=404, detail=f"Camera '{camera}' not found in site '{site}'"
        )

    day_obs = date_validation(date)

    historical: HistoricalPoller = request.app.state.historical
    if await historical.is_busy():
        raise HTTPException(
            status_code=423, detail="Historical data is being processed"
        )

    # Get the night report from historical poller
    night_report = await historical.get_night_report_payload(location, cam, day_obs)

    return {"nightReport": night_report.model_dump() if night_report else None}
