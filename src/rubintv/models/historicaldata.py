from datetime import date
from typing import Dict, List

from google.api_core.exceptions import NotFound
from google.cloud.storage import Blob, Bucket

from rubintv.models.models import (
    Camera,
    Channel,
    Event,
    Location,
    Night_Reports_Event,
    get_current_day_obs,
)
from rubintv.models.models_assignment import cameras, locations
from rubintv.models.models_helpers import get_prefix_from_date


class HistoricalData:
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over, but means that the full blob contents can be looped over without
    making a request for the full data for each operation.
    """

    def __init__(
        self, location_name: str, bucket: Bucket, minimal_data_load: bool
    ) -> None:
        location: Location = locations[location_name]
        self._location = location
        self._bucket = bucket
        self._events = {}
        self._night_reports = {}
        if not minimal_data_load:
            self._events = self._get_events()
        else:
            self._events = self._get_single_date_events_for_location()
        self._night_reports = self._scrape_night_reports()
        self._lastCall = get_current_day_obs()

    def _get_single_date_events_for_location(
        self,
    ) -> Dict[str, Dict[str, List[Event]]]:
        """Returns minimal events for a Location for a hard-coded date in the method.
        Used when only needing a light-weight cache of data to test the app

        Parameters
        ----------
        location : Location
            The Location object representing the camera site e.g. Summit
        bucket : Bucket
            The GCS bucket to retrive blobs from

        Returns
        -------
        Dict[str, Dict[str, List[Event]]]
            The outer dict is keyed per camera,
            the inner dict is keyed per channel and
            list of Events is sorted by day and sequence number
        """
        blobs = []
        for cam_name in self._location.all_cameras():
            camera: Camera = cameras[cam_name]
            print(f"Trying for: {camera.name}")
            if not camera.online:
                continue
            # date for which there are known to be blobs
            the_date = date(2022, 12, 15)
            channel: Channel
            for channel in camera.channels.values():
                prefix = get_prefix_from_date(channel.prefix, the_date)
                try:
                    found_blobs = list(self._bucket.list_blobs(prefix=prefix))
                    print(f"channel: {channel.name} found {len(found_blobs)}")
                    blobs += found_blobs
                except NotFound:
                    print(
                        f"Bucket retrieval error. {self._bucket.name} not found"
                    )
        return self._sort_events_from_blobs(blobs)

    def _get_blobs(self) -> List[Blob]:
        """Downloads Blob metadata from the Bucket for every Camera registered
        as having historical data

        Returns
        -------
        List[Blob]
            A list of Blob objects
        """
        print(f"Getting blobs for location: {self._location.name}")
        blobs = []
        for cam_name in self._location.all_cameras():
            cam = cameras[cam_name]
            for channel in cam.channels.values():
                prefix = channel.prefix
                print(f"Trying prefix: {prefix}")
                try:
                    blobs += list(self._bucket.list_blobs(prefix=prefix))
                except NotFound:
                    print(
                        f"Bucket retrieval error. {self._bucket.name} not found"
                    )
                print(f"Total blobs found: {len(blobs)}")
        return blobs

    def reload(self) -> None:
        """Reloads the historical data cache"""
        self._events = self._get_events(reset=True)
        return

    def _scrape_night_reports(
        self,
    ) -> Dict[str, Dict[date, List[Night_Reports_Event]]]:
        """Downloads and builds a cache of Night Report Events

        Returns
        -------
        Dict[str, Dict[str, List[Night_Reports_Event]]]
            A two dimensional dictionary with outer key camera name and
            inner key the date (as a date object) which co-identify
            a list of Night Reports Events objects
        """
        night_reports: Dict[str, Dict] = {}
        for cam_name in self._location.all_cameras():
            cam: Camera = cameras[cam_name]
            if cam.night_reports_prefix:
                prefix = cam.night_reports_prefix
                print(f"Retrieving night reports for {prefix}")
                blobs = list(self._bucket.list_blobs(prefix=prefix))
                if blobs:
                    night_reports[cam_name] = {}
                    for blob in blobs:
                        report = Night_Reports_Event(
                            blob.public_url,
                            prefix,
                            int(blob.time_created.timestamp()),
                            blobname=blob.name,
                        )
                        the_date = report.obs_date
                        if the_date in night_reports[cam_name]:
                            night_reports[cam_name][the_date].append(report)
                        else:
                            night_reports[cam_name].update(
                                {the_date: [report]}
                            )
                    print(f"Found {len(night_reports[cam_name])} reports")
        return night_reports

    def get_night_reports_for(
        self, camera: Camera, obs_date: date
    ) -> List[Night_Reports_Event]:
        """Returns a list of Night Reports Objects for the camera and date

        Parameters
        ----------
        camera : Camera
            The given Camera
        obs_date : date
            The given date

        Returns
        -------
        List[Night_Reports_Event]
            A list of Night Reports Events in time order
        """
        reports = []
        if (
            camera.slug in self._night_reports
            and obs_date in self._night_reports[camera.slug]
        ):
            reports = sorted(
                self._night_reports[camera.slug][obs_date],
                key=lambda x: x.timestamp,
            )
        return reports

    def _get_events(
        self, reset: bool = False
    ) -> Dict[str, Dict[str, List[Event]]]:
        """Returns a dict of dicts of sorted lists of Events

        Either simply returns the cache of events or populates the cache before returning it.
        It will (re)populate the cache if any of the following are True:\n
        - There is no existing cache\n
        - The day has rolled over\n
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
        if reset or not self._events or get_current_day_obs() > self._lastCall:
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
        for cam in cameras.values():
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
        primary_channel = list(camera.channels)[0]
        years = set(
            [
                event.obs_date.year
                for event in self._get_events()[camera_name][primary_channel]
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
        primary_channel = list(camera.channels)[0]
        months = set(
            [
                event.obs_date.month
                for event in self._get_events()[camera_name][primary_channel]
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
        primary_channel = list(camera.channels)[0]
        days = set(
            [
                event.obs_date.day
                for event in self._get_events()[camera_name][primary_channel]
                if event.obs_date.month == month
                and event.obs_date.year == year
            ]
        )
        days_dict = {
            day: self.get_max_event_seq_for_date(
                camera, date(year, month, day)
            )
            for day in sorted(list(days))
        }
        return days_dict

    def get_max_event_seq_for_date(self, camera: Camera, a_date: date) -> int:
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
        primary_channel = list(camera.channels)[0]
        cam_events = self._get_events()[camera_name][primary_channel]
        days_events = [ev for ev in cam_events if ev.obs_date == a_date]
        return days_events[0].seq

    def get_events_for_date(
        self, camera: Camera, a_date: date
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

    def get_most_recent_day(self, camera: Camera) -> date:
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
        primary_channel = list(camera.channels)[0]
        events = self._get_events()[camera_name][primary_channel]
        most_recent = events[0].obs_date
        return most_recent

    def get_most_recent_event(self, camera: Camera, channel: Channel) -> Event:
        """Returns most recent Event for the given Camera

        Parameters
        ----------

        camera : `Camera`
            The given Camera object

        channel : `Channel`
            A Channel of the given camera

        Returns
        -------

        event : `Event`
            The most recent Event for the given Camera

        """
        camera_name = camera.slug
        channel_name = channel.simplename
        events = self._get_events()[camera_name][channel_name]
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
