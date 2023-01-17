"""The main application factory for the rubintv service."""

__all__ = ["create_app"]

from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web
from google.cloud import storage
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from rubintv.config import Configuration
from rubintv.handlers import init_external_routes, init_internal_routes
from rubintv.models.historicaldata import HistoricalData
from rubintv.models.models_assignment import locations


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
    return create_app(load_minimal_data=True)
