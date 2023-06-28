"""Handlers for the app's external root, ``/rubintv/``."""
from itertools import chain
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from rubintv.dependencies import get_templates
from rubintv.handlers.helpers import find_first
from rubintv.models import Camera, Location

__all__ = ["get_home", "external_router", "templates"]

external_router = APIRouter()
"""FastAPI router for all external handlers."""

templates = get_templates()
"""Jinja2 for templating."""


@external_router.get("/", response_class=HTMLResponse, name="home")
async def get_home(
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    """GET ``/rubintv/`` (the app's external root)."""
    logger.info("Request for the app home page")
    locations = request.app.state.fixtures.locations
    return templates.TemplateResponse(
        "home.jinja", {"request": request, "locations": locations}
    )


@external_router.get("/api/location/{location_name}", response_model=Location)
async def get_location(
    location_name: str,
    request: Request,
) -> Location:
    locations = request.app.state.fixtures.locations
    if not (location := await find_first(locations, "name", location_name)):
        raise HTTPException(status_code=404, detail="Location not found.")
    return location


@external_router.get(
    "/api/location/{location_name}/camera/{camera_name}",
    response_model=Tuple[Location, Camera],
)
async def get_location_camera(
    location_name: str,
    camera_name: str,
    request: Request,
) -> Tuple[Location, Camera]:
    locations = request.app.state.fixtures.locations
    if not (location := await find_first(locations, "name", location_name)):
        raise HTTPException(status_code=404, detail="Location not found.")

    cameras = request.app.state.fixtures.cameras
    camera_groups = location.camera_groups.values()
    location_cams = chain(*camera_groups)
    if camera_name not in location_cams or not (
        camera := await find_first(cameras, "name", camera_name)
    ):
        raise HTTPException(status_code=404, detail="Camera not found.")
    return (location, camera)


# @external_router.get(
#     "/api/location/{location_name}/camera/{camera_name}",
#     response_model=Tuple[Location, Camera],
# )


@external_router.get(
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


@external_router.get(
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
    template = "camera"
    if not camera.online:
        template = "not_online"
    return templates.TemplateResponse(
        f"{template}.jinja",
        {"request": request, "location": location, "camera": camera},
    )
