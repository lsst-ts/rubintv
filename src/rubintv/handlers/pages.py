"""Handlers for the app's external root, ``/rubintv/``."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from rubintv.handlers.api import (
    get_camera_current_events,
    get_location,
    get_location_camera,
)
from rubintv.handlers.pages_helpers import make_table_rows_from_columns_by_seq
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
    # use api to get current events
    historical_busy = False
    day_obs: date | None = None
    table = {}
    try:
        event_data = await get_camera_current_events(
            location_name, camera_name, request
        )
        day_obs = event_data["date"]
        if camera.channels:
            table = make_table_rows_from_columns_by_seq(
                event_data, camera.channels
            )
    except HTTPException:
        historical_busy = True

    template = "camera"
    if not camera.online:
        template = "not_online"

    return templates.TemplateResponse(
        f"{template}.jinja",
        {
            "request": request,
            "location": location,
            "camera": camera,
            "camera_json": camera.model_dump(),
            "table": table,
            "date": day_obs,
            "historical_busy": historical_busy,
        },
    )
