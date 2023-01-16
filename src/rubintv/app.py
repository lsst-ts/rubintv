"""The main application factory for the rubintv service."""

__all__ = ["create_app"]

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List

import aiohttp_jinja2
import jinja2
from aiohttp import web
from google.api_core.exceptions import NotFound
from google.cloud import storage
from google.cloud.storage.client import Bucket
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from rubintv.config import Configuration
from rubintv.handlers import init_external_routes, init_internal_routes
from rubintv.models.historicaldata import HistoricalData
from rubintv.models.models_assignment import locations

HEARTBEATS_PREFIX = "heartbeats"


def create_app(load_minimal_data: bool = False) -> web.Application:
    """Create and configure the aiohttp.web application."""
    config = Configuration()
    configure_logging(
        profile=config.profile,
        log_level=config.log_level,
        name=config.logger_name,
    )
    root_app = web.Application()
    root_app["safir/config"] = config

    client = storage.Client()
    bucket_names = {loc.slug: loc.bucket for loc in locations.values()}

    for location, bucket_name in bucket_names.items():
        bucket = client.bucket(bucket_name)
        root_app[f"rubintv/buckets/{location}"] = bucket
        root_app[f"rubintv/cached_data/{location}"] = HistoricalData(
            location, bucket, load_minimal_data
        )

    root_app["rubintv/site_title"] = "RubinTV Display"
    setup_metadata(package_name="rubintv", app=root_app)
    setup_middleware(root_app)
    root_app.add_routes(init_internal_routes())
    root_app.cleanup_ctx.append(init_http_session)
    root_app.cleanup_ctx.append(heartbeat_polling_init)

    sub_app = web.Application()
    aiohttp_jinja2.setup(
        sub_app,
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
    )

    setup_middleware(sub_app)
    sub_app.add_routes(init_external_routes())
    sub_app.add_routes(
        [
            web.static(
                "/static",
                Path(__file__).parent / "static",
                name="static",
                append_version=True,
            ),
        ]
    )

    root_app.add_subapp(f'/{root_app["safir/config"].name}', sub_app)
    return root_app


def setup_middleware(app: web.Application) -> None:
    """Add middleware to the application."""
    app.middlewares.append(bind_logger)


def create_app_light() -> web.Application:
<<<<<<< HEAD
    return create_app(load_minimal_data=True)
=======
    return create_app(minimal_data_load=True)


async def heartbeat_polling_init(app: web.Application) -> AsyncGenerator:
    """Initialise a loop for polling the heartbeats in the bucket"""
    app["heartbeats_poller"] = asyncio.create_task(poll_for_heartbeats(app))
    yield
    app["heartbeats_poller"].cancel()
    await app["heartbeats_poller"]


async def poll_for_heartbeats(app: web.Application) -> None:
    try:
        while True:
            print("Looking for heartbeats:")
            # just use summit bucket to start
            bucket = app["rubintv/buckets/summit"]
            heartbeats_json_arr = get_heartbeats(bucket, HEARTBEATS_PREFIX)
            heartbeats = process_heartbeats(heartbeats_json_arr)
            print(heartbeats)
            app["heartbeats"] = heartbeats
            await asyncio.sleep(30)
    except asyncio.exceptions.CancelledError:
        print("Polling for heartbeats cancelled")


def process_heartbeats(
    heartbeats_json_list: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    heartbeats = {}
    t = time.time()
    for hb in heartbeats_json_list:
        channel = hb["channel"]
        next = hb["nextExpected"]
        curr = hb["currTime"]
        active = next > t
        heartbeats[channel] = {"active": active, "next": next, "curr": curr}
    return heartbeats


def get_heartbeats(bucket: Bucket, prefix: str) -> List[Dict]:
    hb_blobs = list(bucket.list_blobs(prefix=prefix))
    heartbeats = []
    for hb_blob in hb_blobs:
        blob_content = None
        try:
            the_blob = bucket.blob(hb_blob.name)
            blob_content = the_blob.download_as_bytes()
        except NotFound:
            print(f"Error: {hb_blob.name} not found.")
        if not blob_content:
            continue
        else:
            hb = json.loads(blob_content)
            hb["url"] = hb_blob.name
            heartbeats.append(hb)
    return heartbeats
>>>>>>> 14bf5ec (Use websocket for heartbeat on camera pages)
