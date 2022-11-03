"""The main application factory for the rubintv service."""

__all__ = ["create_app", "get_current_day_obs"]

import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

import aiohttp_jinja2
import jinja2
from aiohttp import web
from dateutil.tz import gettz
from google.cloud import storage
from google.cloud.storage import Blob, Bucket
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from rubintv.config import Configuration
from rubintv.handlers import init_external_routes, init_internal_routes
from rubintv.models import Camera, Event, cameras


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
    client = storage.Client()
    bucket = client.bucket("rubintv_data")
    root_app["rubintv/gcs_bucket"] = bucket
    root_app["rubintv/historical_data"] = HistoricalData(bucket)
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


def get_current_day_obs() -> datetime.date:
    """Get the current day_obs - the observatory rolls the date over at UTC-12"""
    utc = gettz("UTC")
    nowUtc = datetime.datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs


class HistoricalData:
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over, but means that the full blob contents can be looped over without
    making a request for the full data for each operation.
    """

    def __init__(self, bucket: Bucket) -> None:
        self._bucket = bucket
        self._events = {}
        self._events = self._get_events()
        self._lastCall = get_current_day_obs()

    def _get_blobs(self) -> List[Blob]:
        """Downloads Blob metadata from the Bucket for every Camera registered
        as having historical data

        Returns
        -------
        List[Blob]
            A list of Blob objects
        """
        blobs = []
        cameras_with_history = [
            cam for cam in cameras.values() if cam.has_historical
        ]
        for cam in cameras_with_history:
            for channel in cam.channels.values():
                prefix = channel.prefix
                print(f"Trying prefix: {prefix}")
                blobs += list(self._bucket.list_blobs(prefix=prefix))
                print(f"Total blobs found: {len(blobs)}")
        return blobs

    def reload(self) -> None:
        """Reloads the historical data cache"""
        self._events = self._get_events(reset=True)
        self._lastCall = get_current_day_obs()
        return

    def _get_events(
        self, reset: bool = False
    ) -> Dict[str, Dict[str, List[Event]]]:
        """Returns a dict of dicts of sorted lists of Events

        Either simply returns the cache of events or populates the cache before returning it.
        It will (re)populate the cache if any of the following are True:
        - There is no existing cache
        - The day has rolled over
        - reset is set to True


        Parameters
        ----------
        reset : bool, optional
            if True causes the cache of events to be reloaded, by default False

        Returns
        -------
        Dict[str, Dict[str, List[Event]]]
            The outer dict is keyed per camera,
            the inner dict is keyed per channel and
            list of Events is sorted by day and sequence number
        """
        if not self._events or get_current_day_obs() > self._lastCall or reset:
            blobs = self._get_blobs()
            self._events = self._sort_events_from_blobs(blobs)
            self._lastCall = get_current_day_obs()
        return self._events

    def _sort_events_from_blobs(
        self, blobs: List
    ) -> Dict[str, Dict[str, List[Event]]]:
        """Returns a dict of dicts of sorted lists of Events

        This method takes a list of Blobs, filters out any that don't match the
        filetypes associated with camera events then recasts and sorts them as Events
        by day and sequence number.
        Those Events are then organised by channel and camera to which they belong.

        Parameters
        ----------
        blobs : List
            A list of blobs

        Returns
        -------
        Dict[str, Dict[str, List[Event]]]
            The outer dict is keyed per camera,
            the inner dict is keyed per channel and
            list of Events is sorted by day and sequence number
        """
        all_events = [
            Event(blob.public_url)
            for blob in blobs
            if list(filter(blob.public_url.endswith, [".png", ".jpg", ".mp4"]))
            != []
        ]
        s_events = sorted(
            all_events, key=lambda x: (x.obs_date, x.seq), reverse=True
        )
        events_dict: Dict[str, Dict[str, List[Event]]] = {}
        cameras_with_history = [
            cam for cam in cameras.values() if cam.has_historical
        ]
        for cam in cameras_with_history:
            channels = cam.channels
            events_dict[cam.slug] = {}
            for channel in channels:
                events_dict[cam.slug][channel] = [
                    e for e in s_events if e.prefix == channels[channel].prefix
                ]
        return events_dict

    def get_years(self, camera: Camera) -> List[int]:
        """Returns a list of years for a given Camera in which there are Events in the bucket

        Parameters
        ----------
        camera : Camera
            The given Camera

        Returns
        -------
        List[int]
            A list of years
        """
        camera_name = camera.slug
        years = set(
            [
                event.obs_date.year
                for event in self._get_events()[camera_name]["monitor"]
            ]
        )
        return list(years)

    def get_months_for_year(self, camera: Camera, year: int) -> List[int]:
        """Returns a list of months for the given Camera and year
        for which there are Events in the bucket

        Parameters
        ----------
        camera : Camera
            The given Camera
        year : int
            The given year

        Returns
        -------
        List[int]
            List of month numbers (1...12)
        """
        camera_name = camera.slug
        months = set(
            [
                event.obs_date.month
                for event in self._get_events()[camera_name]["monitor"]
                if event.obs_date.year == year
            ]
        )
        reverse_months = sorted(months, reverse=True)
        return list(reverse_months)

    def get_days_for_month_and_year(
        self, camera: Camera, month: int, year: int
    ) -> Dict[int, int]:
        """Given a Camera, year and number of month returns a dict of all
        the days that have a record of Events with the seq_num of the last
        Event for each day.

        The dict is keyed by each day number with the corresponding value
        of the last sequence number of Events recorded that day

        Parameters
        ----------
        camera : Camera
            The given Camera
        month : int
            The given month (1...12)
        year : int
            The given year

        Returns
        -------
        Dict[int, int]
            A dict with day number for key and last seq_num for that day as value
        """
        camera_name = camera.slug
        days = set(
            [
                event.obs_date.day
                for event in self._get_events()[camera_name]["monitor"]
                if event.obs_date.month == month
                and event.obs_date.year == year
            ]
        )
        days_dict = {
            day: self.get_max_event_seq_for_date(
                camera, datetime.date(year, month, day)
            )
            for day in sorted(list(days))
        }
        return days_dict

    def get_max_event_seq_for_date(
        self, camera: Camera, a_date: datetime.date
    ) -> int:
        """Takes a Camera and date and returns the highest sequence number
        for Events recorded on that date (i.e. the last Event)

        Parameters
        ----------
        camera : Camera
            The given Camera
        a_date : datetime.date
            The given date

        Returns
        -------
        int
            The seq_num of the last Event for that Camera and day
        """
        camera_name = camera.slug
        cam_events = self._get_events()[camera_name]["monitor"]
        days_events = [ev for ev in cam_events if ev.obs_date == a_date]
        return days_events[0].seq

    def get_events_for_date(
        self, camera: Camera, a_date: datetime.date
    ) -> Dict[str, List[Event]]:
        """Takes a Camera and date and returns a dict of list of Events, keyed by
        Channel name

        General return value:
        { 'chan_name1': [Event 1, Event 2, ...], 'chan_name2': [...], ...}

        Parameters
        ----------

        camera : `Camera`
            The given Camera object

        a_date : `datetime.date`
            The date to find Events for

        Returns
        -------

        days_events_dict : `Dict[str, List[Event]]`
        """
        camera_name = camera.slug
        events_dict = self._get_events()[camera_name]
        days_events_dict = {}
        for channel in events_dict:
            days_events_dict[channel] = [
                event
                for event in events_dict[channel]
                if event.obs_date == a_date
            ]
        return days_events_dict

    def get_most_recent_day(self, camera: Camera) -> datetime.date:
        """Returns most recent day for which there is data in the bucket for
        the given Camera

        Parameters
        ----------

        camera : `Camera`
            The given Camera object

        Returns
        -------

        most_recent : `datetime.date`
            The date of the most recent day's Event
        """
        camera_name = camera.slug
        events = self._get_events()[camera_name]["monitor"]
        most_recent = events[0].obs_date
        return most_recent

    def get_most_recent_event(self, camera: Camera) -> Event:
        """Returns most recent Event for the given Camera

        Parameters
        ----------

        camera : `Camera`
            The given Camera object

        Returns
        -------

        event : `Event`
            The most recent Event for the given Camera

        """
        camera_name = camera.slug
        events = self._get_events()[camera_name]["monitor"]
        return events[0]

    def get_camera_calendar(
        self, camera: Camera
    ) -> Dict[int, Dict[int, Dict[int, int]]]:
        """Returns a dict representing a calendar for the given Camera

        Provides a dict of days and last seq_num of Events, within a dict of months, within
        a dict keyed by year for the given Camera.

        Parameters
        ----------

        camera : `Camera`
            The given Camera object

        Returns
        -------

        years : `Dict[int, Dict[int, Dict[int, int]]]`
            A data structure for the view to iterate over with years, months, days and num. of
            events for that day for the given Camera

        """
        active_years = self.get_years(camera)
        reverse_years = sorted(active_years, reverse=True)
        years = {}
        for year in reverse_years:
            months = self.get_months_for_year(camera, year)
            months_days = {
                month: self.get_days_for_month_and_year(camera, month, year)
                for month in months
            }
            years[year] = months_days
        return years
