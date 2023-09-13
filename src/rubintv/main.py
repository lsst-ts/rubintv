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
from moto import mock_s3
from safir.dependencies.http_client import http_client_dependency
from safir.logging import configure_logging, configure_uvicorn_logging
from safir.middleware.x_forwarded import XForwardedMiddleware

from .background.bucketpoller import BucketPoller
from .config import config
from .handlers.api import api_router
from .handlers.external import external_router
from .handlers.internal import internal_router
from .handlers.websocket import ws_router
from .mockdata import mock_up_data
from .models.models_init import ModelsInitiator
from .s3bucketinterface import S3BucketInterface

__all__ = ["app", "config"]


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name="rubintv",
)
configure_uvicorn_logging(config.log_level)

# Initialise model data fixtures
models = ModelsInitiator()

# initialise the background bucket poller
bp = BucketPoller(models.locations)
bucket = S3BucketInterface()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Start mocking for s3 buckets.
    # Remove when actual s3 is populated.
    mock = mock_s3()
    mock.start()

    # Generate mock test buckets
    # Remove when actual s3 is populated.
    mock_up_data(models.locations, models.cameras)

    # start polling buckets for data
    today_polling = asyncio.create_task(bp.poll_buckets_for_todays_data())

    yield

    today_polling.cancel()
    # Remove mocking when actual s3 is populated.
    mock.stop()
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

app.state.models = models
app.state.bucket_poller = bp
app.state.bucket = bucket
# app.state.connected_clients = connected_clients

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
app.include_router(external_router, prefix=f"{config.path_prefix}")

# Add middleware.
app.add_middleware(XForwardedMiddleware)
