"""Handlers for the app's external root, ``/rubintv/``."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from rubintv.handlers.api import (
    current_night_report_exists,
    get_calendar_of_historical_events,
    get_camera_current_events,
    get_camera_events_for_date,
    get_current_channel_event,
    get_current_night_report,
    get_location,
    get_location_camera,
    get_most_recent_historical_data,
    get_night_report_for_date,
    get_specific_channel_event,
    night_report_exists_for,
)
from rubintv.handlers.pages_helpers import (
    calendar_factory,
    get_per_day_channels,
    make_table_rows_from_columns_by_seq,
    month_names,
)
from rubintv.models.helpers import find_first
from rubintv.models.models import (
    Channel,
    Event,
    EventJSONDict,
    NightReportDataDict,
)
from rubintv.s3client import S3Client
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
    return templates.TemplateResponse(
        "home.jinja", {"request": request, "locations": locations}
    )


@pages_router.get(
    "/event_image/{location_name}/{camera_name}/{channel_name}/{filename}",
    response_class=StreamingResponse,
    name="event_image",
)
def proxy_image(
    location_name: str,
    camera_name: str,
    channel_name: str,
    filename: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> StreamingResponse:
    try:
        to_remove = "_".join((camera_name, channel_name)) + "_"
        rest = filename.replace(to_remove, "")
        date_str, seq_ext = rest.split("_")
        seq_str, ext = seq_ext.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/{channel_name}/{seq_str}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    data_stream = s3_client.get_raw_object(key)
    return StreamingResponse(content=data_stream.iter_chunks())


@pages_router.get(
    "/plot_image/{location_name}/{camera_name}/{group_name}/{filename}",
    response_class=StreamingResponse,
    name="plot_image",
)
def proxy_plot_image(
    location_name: str,
    camera_name: str,
    group_name: str,
    filename: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> StreamingResponse:
    # auxtel_night_report_2023-08-16_Coverage_airmass

    try:
        to_remove = "_".join((camera_name, "night_report")) + "_"
        rest = filename.replace(to_remove, "")
        date_str = rest.split("_")[0]
        burn, ext = rest.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/night_report/{group_name}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    data_stream = s3_client.get_raw_object(key)
    return StreamingResponse(content=data_stream.iter_chunks())


@pages_router.get(
    "/event_video/{location_name}/{camera_name}/{channel_name}/{filename}",
    response_class=StreamingResponse,
    name="event_video",
)
def proxy_video(
    location_name: str,
    camera_name: str,
    channel_name: str,
    filename: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> StreamingResponse:
    try:
        to_remove = "_".join((camera_name, channel_name)) + "_"
        rest = filename.replace(to_remove, "")
        date_str, seq_ext = rest.split("_")
        seq_str, ext = seq_ext.split(".")
    except ValueError:
        raise HTTPException(404, "Filename not valid.")
    key = f"{camera_name}/{date_str}/{channel_name}/{seq_str}/{filename}"
    s3_client: S3Client = request.app.state.s3_clients[location_name]
    video = s3_client.get_raw_object(key)
    return StreamingResponse(
        content=video.iter_chunks(), status_code=206, media_type="video/mp4"
    )


@pages_router.get(
    "/{location_name}", response_class=HTMLResponse, name="location"
)
async def get_location_page(
    location_name: str,
    request: Request,
) -> Response:
    location = await get_location(location_name, request)
    return templates.TemplateResponse(
        "location.jinja", {"request": request, "location": location}
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
    night_report_link = historical_busy = False
    day_obs: date | None = None
    md: dict | None = {}
    events = per_day_channels = table = {}
    try:
        event_data = await get_camera_current_events(
            location_name, camera_name, request
        )
        day_obs = event_data["date"]
        events = event_data["channel_events"]
        md = event_data["metadata"]
        table = await make_table_rows_from_columns_by_seq(
            event_data, camera.seq_channels()
        )
        per_day_channels = await get_per_day_channels(event_data, camera)
        night_report_link = await current_night_report_exists(
            location, camera, request
        )

    except HTTPException:
        historical_busy = True

    template = "camera"
    if not camera.online:
        template = "not_online"
    if camera.name == "allsky":
        template = "allsky"
    if not table and not historical_busy:
        template = "camera_empty"

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "camera_json": camera.model_dump(),
            "events": events,
            "metadata": md,
            "table": table,
            "date": day_obs,
            "historical_busy": historical_busy,
            "per_day_channels": per_day_channels,
            "night_report_link": night_report_link,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/date/{date_str}",
    response_class=HTMLResponse,
    name="camera_for_date",
)
async def get_camera_for_date_page(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online:
        raise HTTPException(404, "Camera not online.")
    historical_busy = False
    night_report_link = False
    day_obs: date | None = None
    md: dict | None = {}
    events = table = calendar = per_day_channels = {}
    try:
        event_data = await get_camera_events_for_date(
            location_name, camera_name, date_str, request
        )
        table = await make_table_rows_from_columns_by_seq(
            event_data, camera.seq_channels()
        )
        day_obs = event_data["date"]
        events = event_data["channel_events"]
        md = event_data["metadata"]
        per_day_channels = await get_per_day_channels(event_data, camera)
        calendar = await get_calendar_of_historical_events(
            location, camera, request
        )
        if day_obs:
            night_report_link = await night_report_exists_for(
                location, camera, day_obs, request
            )
    except HTTPException as http_error:
        # status 423 is raised if the historical data resource is locked
        if http_error.status_code == 423:
            historical_busy = True
        else:
            raise http_error

    template = "historical"
    if camera.name == "allsky":
        template = "allsky-historical"
    if not table and not historical_busy:
        template = "camera_empty"

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "camera_json": camera.model_dump(),
            "events": events,
            "metadata": md,
            "table": table,
            "date": day_obs,
            "historical_busy": historical_busy,
            "calendar": calendar,
            "calendar_frame": calendar_factory(),
            "month_names": month_names(),
            "per_day_channels": per_day_channels,
            "night_report_link": night_report_link,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/historical",
    response_class=HTMLResponse,
    name="historical",
)
async def get_historical_camera_page(
    location_name: str, camera_name: str, request: Request
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    if not camera.online:
        raise HTTPException(404, "Camera not online.")
    night_report_link = historical_busy = False
    day_obs: date | None = None
    events: dict[str, list[Event]] = {}
    md: dict | None = {}
    table = calendar = per_day_channels = {}
    try:
        h_data = await get_most_recent_historical_data(
            location, camera, request
        )
        if h_data:
            (day_obs, events, md) = h_data
            event_data: EventJSONDict = {
                "date": day_obs,
                "channel_events": events,
                "metadata": md,
            }
            table = await make_table_rows_from_columns_by_seq(
                event_data, camera.seq_channels()
            )
            per_day_channels = await get_per_day_channels(event_data, camera)
            calendar = await get_calendar_of_historical_events(
                location, camera, request
            )
            night_report_link = await night_report_exists_for(
                location, camera, day_obs, request
            )

    except HTTPException:
        historical_busy = True

    template = "historical"
    if camera.name == "allsky":
        template = "allsky-historical"
    if not table and not historical_busy and not historical_busy:
        template = "camera_empty"

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "camera_json": camera.model_dump(),
            "events": events,
            "metadata": md,
            "table": table,
            "date": day_obs,
            "historical_busy": historical_busy,
            "calendar": calendar,
            "calendar_frame": calendar_factory(),
            "month_names": month_names(),
            "per_day_channels": per_day_channels,
            "night_report_link": night_report_link,
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
    nr_data: NightReportDataDict = await get_current_night_report(
        location_name, camera_name, request
    )
    day_obs = nr_data["date"]
    night_report = nr_data["night_report"]
    return templates.TemplateResponse(
        "night-report.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "date": day_obs,
            "night_report": night_report,
        },
    )


@pages_router.get(
    "/{location_name}/{camera_name}/night_report/{date_str}",
    response_class=HTMLResponse,
    name="historical_nr",
)
async def get_historical_night_report_page(
    location_name: str, camera_name: str, date_str: str, request: Request
) -> Response:
    location, camera = await get_location_camera(
        location_name, camera_name, request
    )
    nr_data: NightReportDataDict = await get_night_report_for_date(
        location_name, camera_name, date_str, request
    )
    day_obs = nr_data["date"]
    night_report = nr_data["night_report"]
    return templates.TemplateResponse(
        "night-report-historical.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "date": day_obs,
            "night_report": night_report,
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
    if event:
        channel = find_first(camera.channels, "name", event.channel_name)
    return templates.TemplateResponse(
        "single_event.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "channel": channel,
            "event": event,
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
    if event:
        channel = find_first(camera.channels, "name", event.channel_name)
    return templates.TemplateResponse(
        "current_event.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "channel": channel,
            "event": event,
        },
    )
