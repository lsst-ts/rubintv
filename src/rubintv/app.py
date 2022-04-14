"""The main application factory for the rubintv service."""

__all__ = ["create_app", "getCurrentDayObs"]

from pathlib import Path

from aiohttp import web
from google.cloud import storage
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger
from google.cloud.storage import Bucket
from datetime import date, timedelta

from rubintv.config import Configuration
from rubintv.handlers import init_external_routes, init_internal_routes

from rubintv.models import Event


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
    client = storage.Client.create_anonymous_client()
    bucket = client.bucket('rubintv_data')
    root_app["rubintv/gcs_bucket"] = bucket
    root_app["rubintv/historical_data"] = HistoricalData(bucket)
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
    root_app.add_subapp(f'/{root_app["safir/config"].name}', sub_app)

    return root_app


def setup_middleware(app: web.Application) -> None:
    """Add middleware to the application."""
    app.middlewares.append(bind_logger)


def getCurrentDayObs():
    # XXX do not merge or deploy until this is correct
    today = date.today()
    offset = timedelta(0)  # XXX MFL to provide offset for dayObs rollover
    return today + offset


class HistoricalData():
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over, but means that the full blob contents can be looped over without
    makings a request for the full data for each operation.
    """
    def __init__(self, bucket) -> None:
        # XXX to change back before PR
        # self._blobs = list(bucket.list_blobs())
        with open('/Users/ugy/blobs_store.txt','r') as file:
            self._blobs = file.read().split()
        self._bucket = bucket
        self._lastCall = getCurrentDayObs()

    def _get_blobs(self):
        # XXX to change back before PR
        # if getCurrentDayObs() > self._lastCall:
        #     self._blobs = list(self._bucket.list_blobs())
        #     self._lastCall = getCurrentDayObs()
        return self._blobs

    def _get_events(self):
        # XXX remove _strings before PR
        return self._get_sorted_events_from_blobs_strings(self._get_blobs())

    def _get_sorted_events_from_blobs_strings(self, blobs):
        # XXX remove this method before PR
        events = [Event(blob) for blob in blobs if blob.endswith(".png")]
        sevents = sorted(events, key=lambda x: (x.date, x.seq), reverse=True)
        return sevents

    def get_years(self):
        unique_years = set([event.date.year for event in self._get_events()])
        return list(unique_years)

    def get_months_for_year(self, year):
        months = set([event.date.month for event in self._get_events() if event.date.year == year])
        return list(months)

    def get_days_for_month_and_year(self, month, year):
        days = set([event.date.day for event in self._get_events() if event.date.month == month and event.date.year == year])
        return list(days)

    def get_events_for_date_and_prefix(self, a_date, prefix):
        return [event for event in self._get_events() if event.date.date() == a_date and event.url.startswith(prefix)]
