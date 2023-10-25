"""Handlers for the app's external root, ``/rubintv/``."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from rubintv.handlers.api import (
    get_current_channel_event,
    get_location,
    get_location_camera,
    get_night_report_for_date,
    get_specific_channel_event,
)
from rubintv.handlers.handlers_helpers import (
    get_camera_calendar,
    get_camera_current_data,
    get_camera_events_for_date,
    get_current_night_report_payload,
    get_most_recent_historical_data,
    try_historical_call,
)
from rubintv.handlers.pages_helpers import (
    build_title,
    calendar_factory,
    month_names,
    night_report_to_dict,
    to_dict,
)
from rubintv.models.models import Channel, Event, NightReportPayload
from rubintv.models.models_helpers import date_str_to_date, find_first
from rubintv.templates_init import get_templates

__all__ = ["get_home", "pages_router", "templates"]

pages_router = APIRouter()
"""FastAPI router for all external handlers."""

templates = get_templates()
"""Jinja2 for templating."""


@pages_router.get("/", response_class=HTMLResponse, name="home")
async def get_home(
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    """GET ``/rubintv/`` (the app's external root)."""
    logger.info("Request for the app home page")
    locations = request.app.state.models.locations
    title = build_title()
    return templates.TemplateResponse(
        "home.jinja",
        {"request": request, "locations": locations, "title": title},
    )


@pages_router.get("/admin", response_class=HTMLResponse, name="admin")
async def get_admin_page(request: Request) -> Response:
    title = build_title("Admin")
    return templates.TemplateResponse(
        "admin.jinja", {"request": request, "title": title}
    )


@pages_router.get(
    "/{location_name}", response_class=HTMLResponse, name="location"
)
async def get_location_page(
    location_name: str,
    request: Request,
) -> Response:
    location = await get_location(location_name, request)
    title = build_title(location.title)
    return templates.TemplateResponse(
        "location.jinja",
        {"request": request, "location": location, "title": title},
    )


@pages_router.get(
    "/{location_name}/{camera_name}",
    response_class=HTMLResponse,
    name="camera",
)
async def get_camera_page(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    nr_exists = historical_busy = False
    day_obs: date | None = None
    metadata: dict = {}
    per_day: dict[str, Event] = {}
    channel_data: dict[int, dict[str, dict]] = {}
    try:
        result = await get_camera_current_data(location, camera, request)
        if result:
            (
                day_obs,
                channel_data,
                per_day,
                metadata,
                nr_exists,
            ) = result
    except HTTPException as e:
        if e.status_code == 423:
            historical_busy = True
        else:
            raise e

    template = "camera"
    if not camera.online:
        template = "not_online"
    else:
        if camera.name == "allsky":
            template = "allsky"
        if not day_obs and not historical_busy:
            template = "camera_empty"

    title = build_title(location.title, camera.title, "Current")

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "date": day_obs,
            "location": location,
            "camera": camera.model_dump(),
            "channelData": channel_data,
            "per_day": per_day,
            "metadata": metadata,
            "historical_busy": historical_busy,
            "nr_exists": nr_exists,
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/date/{date_str}",
    response_class=HTMLResponse,
    name="camera_for_date",
)
async def get_camera_for_date_page(
    location_name: str,
    camera_name: str,
    date_str: str,
    request: Request,
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online:
        raise HTTPException(404, "Camera not online.")
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")
    historical_busy = False
    nr_exists = False
    metadata: dict = {}
    per_day: dict[str, Event] = {}
    channel_data: dict[int, dict[str, dict]] = {}
    calendar: dict[int, dict[int, dict[int, int]]] = {}
    try:
        data = await get_camera_events_for_date(
            location, camera, day_obs, request
        )
        if data:
            channel_data, per_day, metadata, nr_exists = data
            calendar = await get_camera_calendar(location, camera, request)

    except HTTPException as http_error:
        # status 423 is raised if the historical data resource is locked
        if http_error.status_code == 423:
            historical_busy = True
        else:
            raise http_error

    template = "historical"
    if camera.name == "allsky":
        template = "allsky-historical"
    if not calendar and not historical_busy:
        template = "camera_empty"

    title = build_title(location.title, camera.title, date_str)

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "date": day_obs,
            "location": location,
            "camera": camera.model_dump(),
            "channelData": channel_data,
            "per_day": per_day,
            "metadata": metadata,
            "historical_busy": historical_busy,
            "nr_exists": nr_exists,
            "calendar": calendar,
            "calendar_frame": calendar_factory(),
            "month_names": month_names(),
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/historical",
    response_class=HTMLResponse,
    name="historical",
)
async def get_historical_camera_page(
    location_name: str,
    camera_name: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online:
        raise HTTPException(404, "Camera not online.")
    historical_busy = False
    nr_exists = False
    day_obs: date | None = None
    metadata: dict = {}
    per_day: dict[str, Event] = {}
    channel_data: dict[int, dict[str, dict]] = {}
    calendar: dict[int, dict[int, dict[int, int]]] = {}
    try:
        data = await get_most_recent_historical_data(location, camera, request)
        if data:
            day_obs, channel_data, per_day, metadata, nr_exists = data
            calendar = await get_camera_calendar(location, camera, request)
    except HTTPException as e:
        if e.status_code == 423:
            historical_busy = True
        else:
            raise e

    template = "historical"
    if camera.name == "allsky":
        template = "allsky-historical"
    if not calendar and not historical_busy:
        template = "camera_empty"

    title = build_title(location.title, camera.title, "Historical")

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "date": day_obs,
            "location": location,
            "camera": camera.model_dump(),
            "channelData": channel_data,
            "per_day": per_day,
            "metadata": metadata,
            "historical_busy": historical_busy,
            "nr_exists": nr_exists,
            "calendar": calendar,
            "calendar_frame": calendar_factory(),
            "month_names": month_names(),
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/night_report",
    response_class=HTMLResponse,
    name="night_report",
)
async def get_current_night_report_page(
    location_name: str, camera_name: str, request: Request
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    day_obs: date | None = None
    day_obs, night_report = await get_current_night_report_payload(
        location, camera, request
    )

    title = build_title(location.title, camera.title, "Current Night Report")

    return templates.TemplateResponse(
        "night-report.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "date": day_obs,
            "night_report": await night_report_to_dict(night_report),
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/night_report/{date_str}",
    response_class=HTMLResponse,
    name="historical_nr",
)
async def get_historical_night_report_page(
    location_name: str,
    camera_name: str,
    date_str: str,
    request: Request,
    # logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    try:
        day_obs = date_str_to_date(date_str)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date.")

    night_report: NightReportPayload
    night_report, historical_busy = await try_historical_call(
        get_night_report_for_date,
        location_name,
        camera_name,
        date_str,
        request,
    )

    title = build_title(
        location.title,
        camera.title,
        f"Night Report for {date_str}",
    )

    return templates.TemplateResponse(
        "night-report-historical.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "date": day_obs,
            "night_report": await night_report_to_dict(night_report),
            "historical_busy": historical_busy,
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/event",
    response_class=HTMLResponse,
    name="single_event",
)
async def get_specific_channel_event_page(
    location_name: str,
    camera_name: str,
    key: str,
    request: Request,
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    event = await get_specific_channel_event(
        location_name, camera_name, key, request
    )
    channel: Channel | None = None
    channel_title = ""
    event_detail = ""
    if event:
        event_detail = f"{event.day_obs}/${event.seq_num}"
        channel = find_first(camera.channels, "name", event.channel_name)
    if channel:
        channel_title = channel.title

    title = build_title(
        location.title, camera.title, channel_title, event_detail
    )

    return templates.TemplateResponse(
        "single_event.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "channel": to_dict(channel),
            "event": to_dict(event),
            "title": title,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/current/{channel_name}",
    response_class=HTMLResponse,
    name="current_event",
)
async def get_current_channel_event_page(
    location_name: str, camera_name: str, channel_name: str, request: Request
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    event = await get_current_channel_event(
        location_name, camera_name, channel_name, request
    )
    channel: Channel | None = None
    channel_title = ""
    if event:
        channel = find_first(camera.channels, "name", event.channel_name)
    if channel:
        channel_title = channel.title

    title = build_title(location.title, camera.title, channel_title, "Current")

    return templates.TemplateResponse(
        "current_event.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "channel": to_dict(channel),
            "title": title,
            "event": to_dict(event),
        },
    )
