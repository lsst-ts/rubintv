"""The main application factory for the rubintv service."""

__all__ = ["create_app"]

from pathlib import Path

from aiohttp import web
from google.cloud import storage
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from rubintv.config import Configuration
from rubintv.handlers import init_external_routes, init_internal_routes


def create_app() -> web.Application:
    """Create and configure the aiohttp.web application."""
    config = Configuration()
    configure_logging(
        profile=config.profile,
        log_level=config.log_level,
        name=config.logger_name,
    )

    root_app = web.Application()
    root_app["safir/config"] = config
    root_app["rubintv/gcs_bucket"] = storage.client().get_bucket(
        config.bucket_name
    )
    setup_metadata(package_name="rubintv", app=root_app)
    setup_middleware(root_app)
    root_app.add_routes(init_internal_routes())
    root_app.cleanup_ctx.append(init_http_session)

    sub_app = web.Application()
    setup_middleware(sub_app)
    sub_app.add_routes(init_external_routes())
    sub_app.add_routes(
        [
            web.static(
                "/static", Path(__file__).parent / "static", name="static"
            ),
        ]
    )
    sub_app.add_routes(
        [
            web.static(
                "/images", Path(__file__).parent / "images", name="images"
            ),
        ]
    )
    root_app.add_subapp(f'/{root_app["safir/config"].name}', sub_app)

    return root_app


def setup_middleware(app: web.Application) -> None:
    """Add middleware to the application."""
    app.middlewares.append(bind_logger)
