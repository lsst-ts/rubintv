"""The main application factory for the rubintv service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import redis.asyncio as redis  # type: ignore[import]
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from redis.exceptions import ConnectionError, TimeoutError  # type: ignore[import]

from . import __version__
from .background.clusterstatushandler import DetectorStatusHandler
from .background.currentpoller import CurrentPoller
from .background.historicaldata import HistoricalPoller
from .config import config, rubintv_logger
from .handlers.api import api_router
from .handlers.ddv_routes_handler import ddv_router
from .handlers.ddv_websocket_handler import ddv_client_ws_router, internal_ws_router
from .handlers.heartbeat_server import heartbeat_ws_router
from .handlers.internal import internal_router
from .handlers.pages import pages_router
from .handlers.proxies import proxies_router
from .handlers.websocket import data_ws_router
from .handlers.websockets_clients import clients
from .middleware.x_forwarded import XForwardedMiddleware
from .models.models_init import ModelsInitiator
from .s3client import S3Client

logger = rubintv_logger()

exp_checker_installed = False
try:
    from lsst.ts.exp_checker import app as exp_checker_app

    logger.info("exp_checker is mounted")
    exp_checker_installed = True
except (ModuleNotFoundError, ImportError):
    logger.warn("exp-checker not found. Not mounting.")

__all__ = ["app", "config"]

logger.info("redis host:", redis_host=config.ra_redis_host)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Initialise model data fixtures
    models = ModelsInitiator()

    # initialise the background bucket pollers
    hp = HistoricalPoller(models.locations)

    # initialise the redis client
    redis_client = None
    redis_subscriber = None
    if config.ra_redis_host:
        redis_client = await _makeRedis()
    if redis_client:
        redis_subscriber = DetectorStatusHandler(
            redis_client=redis_client,
            mapped_keys=models.redis_detectors,
            text_keys=models.redis_cluster_text,
        )
        redis_task = asyncio.create_task(redis_subscriber.run_async())
        app.state.redis_client = redis_client
        app.state.redis_subscriber = redis_subscriber
    else:
        redis_task = None
        logger.error("Redis client not created. Redis is not available.")
        app.state.redis_client = None
        app.state.redis_subscriber = None

    # inject app state
    app.state.models = models
    app.state.historical = hp
    app.state.s3_clients = {}
    for location in models.locations:
        app.state.s3_clients[location.name] = S3Client(
            location.profile_name, location.bucket_name, location.endpoint_url
        )

    # start polling buckets for data
    today_polling = await startup_current_poller(models, app)
    historical_polling = asyncio.create_task(hp.check_for_new_day())

    # Startup phase for the subapp
    if exp_checker_installed and exp_checker_app.router.lifespan:
        async with exp_checker_app.router.lifespan_context(exp_checker_app):
            yield  # Yield to the main app with subapp context active

    # If no lifespan is needed for the subapp, still yield to the main app
    else:
        yield

    if redis_task and redis_subscriber is not None:
        await redis_subscriber.stop_async()
        redis_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass

    historical_polling.cancel()
    today_polling.cancel()

    if redis_client is not None:
        try:
            await redis_client.aclose()  # type: ignore
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection error: {e}")

    for c in clients.values():
        await c.close()


async def startup_current_poller(models: ModelsInitiator, app: FastAPI) -> asyncio.Task:
    """Start the current poller.
    Parameters
    ----------
    models : dict
        The models dictionary.
    app : FastAPI
        The FastAPI application.
    """
    first_pass = asyncio.Event()
    cp = CurrentPoller(models.locations, first_pass_event=first_pass)
    app.state.current_poller = cp
    # Create an event to signal the first pass is complete
    app.state.first_pass_event = first_pass
    return asyncio.create_task(cp.poll_buckets_for_todays_data())


async def _makeRedis() -> redis.Redis | None:
    """Create a Redis client.
    Returns
    -------
    redis.Redis | None
        The Redis client or None if the connection fails.
    """
    SOCKET_TIMEOUT = 3
    host: str = config.ra_redis_host
    password = config.ra_redis_password
    port: int = config.ra_redis_port
    redis_client = await redis.Redis(
        host=host, password=password, port=port, socket_timeout=SOCKET_TIMEOUT
    )
    try:
        await redis_client.ping()
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        return None
    return redis_client


def create_app() -> FastAPI:
    """The main FastAPI application for rubintv."""
    app = FastAPI(
        title=config.name,
        description="rubinTV is a Web app to display Butler-served data sets",
        version=__version__,
        openapi_url=f"{config.path_prefix}/openapi.json",
        docs_url=f"{config.path_prefix}/docs",
        redoc_url=f"{config.path_prefix}/redoc",
        debug=True,
        lifespan=lifespan,
    )

    # Intwine webpack assets
    # generated with npm run build
    if os.path.isdir("assets"):
        app.mount(
            f"{config.path_prefix}/static/assets",
            StaticFiles(directory="assets"),
            name="static-assets",
        )

    # Intwine jinja2 templating
    app.mount(
        f"{config.path_prefix}/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    external_ws_router_prefix = f"{config.path_prefix}/ws"

    # Mount Derived Data Visualization Flutter app.
    ddv_app_root = "ddv/build/web"
    if os.path.isdir(ddv_app_root):
        app.mount(
            f"{config.path_prefix}/ddv",
            StaticFiles(directory=ddv_app_root, html=True),
            name="ddv-flutter",
        )
        app.state.ddv_path = ddv_app_root
        # Attach DDV Flutter client websocket (external):
        app.include_router(
            ddv_client_ws_router, prefix=f"{external_ws_router_prefix}/ddv"
        )
        # Provide router that hooks up ddv/index.html
        app.include_router(ddv_router, prefix=f"{config.path_prefix}/ddv")

    # Mount exp_checker FastAPI app.
    if exp_checker_installed:
        app.mount(f"{config.path_prefix}/exp_checker", exp_checker_app)

    # Attach the routers.

    # Internal routing:
    app.include_router(internal_router)
    # Below includes DDV worker pod websocket (internal):
    app.include_router(internal_ws_router, prefix="/ws")

    # External websocket routing:
    app.include_router(data_ws_router, prefix=f"{external_ws_router_prefix}/data")
    app.include_router(
        heartbeat_ws_router, prefix=f"{external_ws_router_prefix}/heartbeats"
    )

    # External HTTP routing:
    app.include_router(api_router, prefix=f"{config.path_prefix}/api")
    app.include_router(proxies_router, prefix=f"{config.path_prefix}")
    app.include_router(pages_router, prefix=f"{config.path_prefix}")

    # Add middleware.
    app.add_middleware(XForwardedMiddleware)

    return app


app = create_app()
