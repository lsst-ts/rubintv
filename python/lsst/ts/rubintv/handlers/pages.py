"""Handlers for the app's external root, ``/rubintv/``."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.api import (
    get_current_channel_event,
    get_location,
    get_location_camera,
    get_night_report_for_date,
    get_specific_channel_event,
)
from lsst.ts.rubintv.handlers.handlers_helpers import (
    date_validation,
    get_camera_calendar,
    get_camera_current_data,
    get_camera_events_for_date,
    get_current_night_report_payload,
    get_latest_metadata,
    get_most_recent_historical_day,
    get_prev_next_event,
    try_historical_call,
)
from lsst.ts.rubintv.handlers.pages_helpers import (
    build_title,
    get_admin,
    get_key_from_type_and_visit,
    to_dict,
)
from lsst.ts.rubintv.models.models import (
    CameraPageData,
    Channel,
    Location,
    NightReport,
    get_current_day_obs,
)
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.templates_init import get_templates

__all__ = ["get_home", "pages_router", "templates"]

pages_router = APIRouter()
"""FastAPI router for all external handlers."""

templates = get_templates()
"""Jinja2 for templating."""

logger = rubintv_logger()


@pages_router.get("/", response_class=HTMLResponse, name="home")
async def get_home(
    request: Request,
) -> Response:
    """GET ``/rubintv/`` (the app's external root)."""
    locations: list[Location] = request.app.state.models.locations
    try:
        ddv_installed = request.app.state.ddv_path is not None
    except AttributeError:  # pragma: no cover
        ddv_installed = False
    admin = await get_admin(request)
    title = build_title()
    return templates.TemplateResponse(
        request=request,
        name="home.jinja",
        context={
            "request": request,
            "locations": locations,
            "title": title,
            "ddv_installed": ddv_installed,
            "admin": admin,
        },
    )


@pages_router.get("/admin", response_class=HTMLResponse, name="admin")
async def get_admin_page(request: Request) -> Response:
    admin = await get_admin(request)
    if admin is None:
        raise HTTPException(status_code=403, detail="Access forbidden.")
    title = build_title("Admin")
    return templates.TemplateResponse(
        request=request,
        name="admin.jinja",
        context={"request": request, "title": title, "admin": admin},
    )


@pages_router.get("/slac", response_class=RedirectResponse)
async def redirect_slac_no_slash(request: Request) -> RedirectResponse:
    new_url = request.url.replace(path="/rubintv/usdf")
    return RedirectResponse(url=str(new_url), status_code=301)


@pages_router.get("/slac/{path:path}", response_class=RedirectResponse)
async def redirect_slac(path: str | None, request: Request) -> RedirectResponse:
    old_path = request.url.path
    new_path = old_path.replace("/slac", "/usdf", 1)
    new_url = request.url.replace(path=new_path)
    return RedirectResponse(url=str(new_url), status_code=301)


@pages_router.get("/{location_name}", response_class=HTMLResponse, name="location")
async def get_location_page(
    location_name: str,
    request: Request,
) -> Response:
    location = await get_location(location_name, request)
    title = build_title(location.title)
    return templates.TemplateResponse(
        request=request,
        name="location.jinja",
        context={"request": request, "location": location, "title": title},
    )


@pages_router.get(
    "/{location_name}/{camera_name}",
    response_class=Response,
    name="camera",
)
async def get_camera_page(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Response:
    """GET ``/rubintv/{location_name}/{camera_name}``
    (the camera page for the current day)."""
    day_obs = get_current_day_obs()
    return await get_camera_for_date_page(
        location_name=location_name,
        camera_name=camera_name,
        date_str=day_obs.isoformat(),
        request=request,
    )


@pages_router.get(
    "/{location_name}/{camera_name}/mosaic",
    response_class=HTMLResponse,
    name="camera_mosaic",
)
async def get_camera_mosaic_page(
    location_name: str,
    camera_name: str,
    request: Request,
    headerless: bool = False,
) -> Response:
    """GET ``/rubintv/{location_name}/{camera_name}/mosaic``
    Collects together a page of updating images from the camera.
    """
    logger.info("Getting mosaic page", headerless=headerless)
    location, camera = await get_location_camera(location_name, camera_name, request)

    # check if the camera has a mosaic view (see models_data.yaml)
    if not camera.mosaic_view_meta:
        raise HTTPException(404, "No mosaic found for this camera.")

    day_obs = get_current_day_obs()

    title = build_title(location.title, camera.title, "Current Mosaic")
    return templates.TemplateResponse(
        request=request,
        name="mosaic.jinja",
        context={
            "request": request,
            "date": day_obs,
            "location": location,
            "camera": camera.model_dump(),
            "title": title,
            "headerless": headerless,
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
    location, camera = await get_location_camera(location_name, camera_name, request)

    if date_str != "historical":
        day_obs = date_validation(date_str)
    else:
        day_obs = None
    if not camera.online:
        raise HTTPException(404, "Camera not online.")

    data: CameraPageData = CameraPageData()
    stale_data = False
    no_data_at_all = False

    is_historical = True
    current_day_obs = get_current_day_obs()
    if day_obs == current_day_obs:
        is_historical = False
        data = await get_camera_current_data(location, camera, request)
        if data.is_empty():
            stale_data = True

    historical_busy = False
    try:
        if (day_obs == current_day_obs and data.is_empty()) or date_str == "historical":
            day_obs = await get_most_recent_historical_day(location, camera, request)
        if day_obs is not None and data.is_empty():
            data = await get_camera_events_for_date(location, camera, day_obs, request)
        if day_obs is None:
            no_data_at_all = True

    except HTTPException as http_error:
        # status 423 is raised if the historical data resource is locked
        if http_error.status_code == 423:
            historical_busy = True
        else:
            raise http_error

    calendar: dict[int, dict[int, dict[int, int]]] = {}
    if is_historical:
        calendar = await get_camera_calendar(location, camera, request)

    nr_link = ""
    if not data.is_empty() and data.nr_exists:
        nr_link = "historical"

    template = "camera"
    if camera.name == "allsky":
        template = "allsky"
    if data is None and not historical_busy:
        template = "not-on-this-day"
    if no_data_at_all and not historical_busy:
        template = "camera-empty"

    title = build_title(location.title, camera.title, date_str)

    return templates.TemplateResponse(
        request=request,
        name=f"{template}.jinja",
        context={
            "request": request,
            "date": day_obs,
            "isHistorical": is_historical,
            "location": location,
            "camera": camera.model_dump(),
            "channelData": data.channel_data,
            "perDay": data.per_day,
            "metadata": data.metadata,
            "historicalBusy": historical_busy,
            "nr_link": nr_link,
            "calendar": calendar,
            "title": title,
            "isStale": stale_data,
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
) -> Response:
    redirect_url = request.url_for(
        "camera_for_date",
        location_name=location_name,
        camera_name=camera_name,
        date_str="historical",
    )
    return RedirectResponse(redirect_url)


@pages_router.get(
    "/{location_name}/{camera_name}/night_report",
    response_class=HTMLResponse,
    name="night_report",
)
async def get_current_night_report_page(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Response:
    location, camera = await get_location_camera(location_name, camera_name, request)
    day_obs: date | None = None
    day_obs, night_report = await get_current_night_report_payload(
        location, camera, request
    )

    title = build_title(location.title, camera.title, "Current Night's Evolution")

    return templates.TemplateResponse(
        request=request,
        name="night-report.jinja",
        context={
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "date": day_obs,
            "night_report": night_report.model_dump(),
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
) -> Response:
    location, camera = await get_location_camera(location_name, camera_name, request)

    day_obs = date_validation(date_str)

    night_report: NightReport
    night_report, historical_busy = await try_historical_call(
        get_night_report_for_date,
        location_name=location_name,
        camera_name=camera_name,
        date_str=date_str,
        request=request,
        # default return is empty night report
        is_busy_default=NightReport(),
    )

    title = build_title(
        location.title,
        camera.title,
        f"Night`s evolution for {date_str}",
    )

    return templates.TemplateResponse(
        request=request,
        name="night-report-historical.jinja",
        context={
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "date": day_obs,
            "night_report": night_report.model_dump(),
            "historicalBusy": historical_busy,
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
    request: Request,
    key: Optional[str] = None,
    type: Optional[str] = None,
    visit: Optional[str] = None,
) -> Response:
    location, camera = await get_location_camera(location_name, camera_name, request)
    if key is None:
        if type is None or visit is None:
            raise HTTPException(status_code=404, detail="Key not found.")
        key = await get_key_from_type_and_visit(
            camera_name=camera_name,
            type=type,
            visit=visit,
        )
        if key is None:
            raise HTTPException(status_code=404, detail="Key not found.")

    logger.info("Key found", key=key)
    event = await get_specific_channel_event(location_name, camera_name, key, request)
    channel: Channel | None = None
    channel_title = ""
    event_detail = ""
    next_prev: dict[str, str] = {}
    if event:
        event_detail = f"{event.day_obs}/${event.seq_num}"
        channel = find_first(camera.channels, "name", event.channel_name)
    if channel:
        channel_title = channel.title
        next_prev, historical_busy = await try_historical_call(
            get_prev_next_event,
            location=location,
            camera=camera,
            event=event,
            request=request,
        )
        if historical_busy:
            next_prev = {}

    title = build_title(location.title, camera.title, channel_title, event_detail)

    return templates.TemplateResponse(
        request=request,
        name="single_event.jinja",
        context={
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "channel": to_dict(channel),
            "event": to_dict(event),
            "prevNext": next_prev,
            "historicalBusy": historical_busy,
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
    location, camera = await get_location_camera(location_name, camera_name, request)
    event = await get_current_channel_event(
        location_name, camera_name, channel_name, request
    )

    metadata = await get_latest_metadata(location, camera, request)

    channel: Channel = find_first(camera.channels, "name", channel_name)
    if channel is None or channel not in camera.channels:
        raise HTTPException(status_code=404, detail="Channel not found.")

    title = build_title(location.title, camera.title, channel.title, "Current")

    return templates.TemplateResponse(
        request=request,
        name="single_event.jinja",
        context={
            "request": request,
            "location": location,
            "camera": camera.model_dump(),
            "channel": to_dict(channel),
            "title": title,
            "event": to_dict(event),
            "metadata": metadata,
            "isCurrent": True,
        },
    )
