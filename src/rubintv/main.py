"""The main application factory for the rubintv service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

from importlib.metadata import metadata, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from safir.dependencies.http_client import http_client_dependency
from safir.logging import configure_logging, configure_uvicorn_logging
from safir.middleware.x_forwarded import XForwardedMiddleware

from .config import config
from .handlers.external import external_router
from .handlers.internal import internal_router
from .models.buckethandler import BucketHandlerInterface, BucketHandlerMaker
from .models.models_init import ModelsInitiator

__all__ = ["app", "config"]


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name="rubintv",
)
configure_uvicorn_logging(config.log_level)

"""The main FastAPI application for rubintv."""
app = FastAPI(
    title="rubintv",
    description=metadata("rubintv")["Summary"],
    version=version("rubintv"),
    openapi_url=f"/{config.path_prefix}/openapi.json",
    docs_url=f"/{config.path_prefix}/docs",
    redoc_url=f"/{config.path_prefix}/redoc",
    debug=True,
)

# Initialise model data fixtures
m = ModelsInitiator()
app.state.fixtures = m

# Attach a bucket
bhm = BucketHandlerMaker("gcs")
bucket_handler: BucketHandlerInterface = bhm.get_bucket_handler("rubintv_data")
app.state.bucket_handler = bucket_handler

# Intwine jinja2 templating
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

# Attach the routers.
app.include_router(internal_router)
app.include_router(external_router, prefix=f"{config.path_prefix}")

# Add middleware.
app.add_middleware(XForwardedMiddleware)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await http_client_dependency.aclose()
