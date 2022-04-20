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

from rubintv.models import Event, per_event_channels


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
    bucket = client.bucket("rubintv_data")
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


class HistoricalData:
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over, but means that the full blob contents can be looped over without
    makings a request for the full data for each operation.
    """

    def __init__(self, bucket) -> None:
        self._bucket = bucket
        self._events = {}
        self._events = self._get_events()
        self._lastCall = getCurrentDayObs()

    def _get_blobs(self):
        blobs = list(self._bucket.list_blobs())
        return blobs

    def _get_events(self):
        if not self._events or getCurrentDayObs() > self._lastCall:
            print("reading in events...")
            blobs = self._get_blobs()
            self._events = self._get_events_from_blobs(blobs)
            self._lastCall = getCurrentDayObs()
        return self._events

    def _get_events_from_blobs(self, blobs):
        """Returns a dict with keys as per_event_channels and a
        corresponding list of events for each channel
        """
        all_events = [
            Event(blob.public_url)
            for blob in blobs
            if blob.public_url.endswith(".png")
        ]
        s_events = sorted(
            all_events, key=lambda x: (x.date, x.seq), reverse=True
        )
        events_dict = {}
        for channel in per_event_channels:
            events_dict[channel] = [
                e
                for e in s_events
                if e.prefix == per_event_channels[channel].prefix
            ]
        return events_dict

    def get_years(self):
        years = set(
            [event.date.year for event in self._get_events()["monitor"]]
        )
        return list(years)

    def get_months_for_year(self, year):
        months = set(
            [
                event.date.month
                for event in self._get_events()["monitor"]
                if event.date.year == year
            ]
        )
        reverse_months = sorted(months, reverse=True)
        return list(reverse_months)

    def get_days_for_month_and_year(self, month, year):
        days = set(
            [
                event.date.day
                for event in self._get_events()["monitor"]
                if event.date.month == month and event.date.year == year
            ]
        )
        return list(days)

    def get_events_for_date(self, a_date):
        """returns dict of events:
        { 'chan_name1': [Event 1, Event 2, ...], 'chan_name2': [...], ...}
        """
        events_dict = self._get_events()
        days_events_dict = {}
        for channel in events_dict:
            days_events_dict[channel] = [
                event
                for event in events_dict[channel]
                if event.date.date() == a_date
            ]
        return days_events_dict

    def get_second_most_recent_day(self):
        events = self._get_events()["monitor"]
        most_recent = events[0].date
        events = [event for event in events if not (event.date == most_recent)]
        # NB returns a date object not datetime
        second_most = events[0].date.date()
        return second_most
