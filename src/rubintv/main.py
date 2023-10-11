"""The main application factory for the rubintv service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""
import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import metadata, version
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from safir.dependencies.http_client import http_client_dependency
from safir.logging import configure_logging, configure_uvicorn_logging
from safir.middleware.x_forwarded import XForwardedMiddleware

from .background.currentpoller import CurrentPoller
from .background.historicaldata import HistoricalPoller
from .config import config
from .handlers.api import api_router
from .handlers.internal import internal_router
from .handlers.pages import pages_router
from .handlers.websocket import ws_router
from .handlers.websockets_clients import clients
from .models.models_init import ModelsInitiator
from .s3client import S3Client

__all__ = ["app", "config"]


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name=config.name,
)
configure_uvicorn_logging(config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Initialise model data fixtures
    models = ModelsInitiator()

    # initialise the background bucket pollers
    cp = CurrentPoller(models.locations)
    hp = HistoricalPoller(models.locations)

    # inject app state
    app.state.models = models
    app.state.current_poller = cp
    app.state.historical = hp
    app.state.s3_clients = {}
    for location in models.locations:
        app.state.s3_clients[location.name] = S3Client(location.bucket_name)

    # start polling buckets for data
    today_polling = asyncio.create_task(cp.poll_buckets_for_todays_data())
    historical_polling = asyncio.create_task(hp.check_for_new_day())

    yield

    historical_polling.cancel()
    today_polling.cancel()
    for c in clients.values():
        await c.close()
    await http_client_dependency.aclose()


"""The main FastAPI application for rubintv."""
app = FastAPI(
    title="rubintv",
    description=metadata("rubintv")["Summary"],
    version=version("rubintv"),
    openapi_url=f"{config.path_prefix}/openapi.json",
    docs_url=f"{config.path_prefix}/docs",
    redoc_url=f"{config.path_prefix}/redoc",
    debug=True,
    lifespan=lifespan,
)

# Intwine jinja2 templating
app.mount(
    "/rubintv/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

# Attach the routers.
app.include_router(internal_router)
app.include_router(api_router, prefix=f"{config.path_prefix}/api")
app.include_router(ws_router, prefix=f"{config.path_prefix}/ws")
app.include_router(pages_router, prefix=f"{config.path_prefix}")

# Add middleware.
app.add_middleware(XForwardedMiddleware)
