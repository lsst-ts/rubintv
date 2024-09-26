import asyncio
import pickle
import re
import zlib
from datetime import date
from time import time
from typing import Any

from lsst.ts.rubintv.background.background_helpers import get_next_previous_from_table
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import notify_all_status_change
from lsst.ts.rubintv.models.models import (
    Camera,
    Channel,
    Event,
    Location,
    NightReport,
    NightReportData,
    get_current_day_obs,
)
from lsst.ts.rubintv.models.models_helpers import (
    make_table_from_event_list,
    objects_to_events,
    objects_to_ngt_report_data,
)
from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger()


class HistoricalPoller:
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over.
    """

    # polling period in seconds
    CHECK_NEW_DAY_PERIOD = 5

    def __init__(self, locations: list[Location], test_mode: bool = False) -> None:
        self._clients: dict[str, S3Client] = {}
        self._metadata: dict[str, bytes] = {}
        self._temp_events: dict[str, list[Event]] = {}
        self._compressed_events: dict[str, bytes] = {}
        self._nr_metadata: dict[str, list[NightReportData]] = {}
        self._calendar: dict[str, dict[int, dict[int, dict[int, int]]]] = {}
        self._locations = locations
        self._clients = {
            location.name: S3Client(location.profile_name, location.bucket_name)
            for location in locations
        }

        self._have_downloaded = False
        self._last_reload = get_current_day_obs()

        self.cam_year_rgx = re.compile(r"(\w+)\/([\d]{4})-[\d]{2}-[\d]{2}")

        self.test_mode = test_mode

    async def clear_all_data(self) -> None:
        self._have_downloaded = False
        self._metadata = {}
        self._compressed_events = {}
        self._nr_metadata = {}
        self._calendar = {}

    async def trigger_reload_everything(self) -> None:
        self._have_downloaded = False

    async def is_busy(self) -> bool:
        return not self._have_downloaded

    async def check_for_new_day(self) -> None:
        try:
            while True:
                if (
                    not self._have_downloaded
                    or self._last_reload < get_current_day_obs()
                ):
                    time_start = time()
                    await self.clear_all_data()
                    for location in self._locations:
                        await self._refresh_location_store(location)

                    self._last_reload = get_current_day_obs()
                    self._have_downloaded = True

                    time_taken = time() - time_start
                    logger.info("Historical polling took:", time_taken=time_taken)

                    await notify_all_status_change(historical_busy=False)
                else:
                    if self.test_mode:
                        break
                    await asyncio.sleep(self.CHECK_NEW_DAY_PERIOD)
        except Exception as e:
            logger.error(e)

    async def _refresh_location_store(self, location: Location) -> None:
        try:
            up_to_date_objects = await self._get_objects(location)
            await self.filter_convert_store_objects(up_to_date_objects, location)
        except Exception as e:
            logger.error(e)

    async def _get_objects(self, location: Location) -> list[dict[str, str]]:
        """Downloads objects from the bucket for each online camera for the
        location.

        Returns
        -------
        objects :  `list` [`dict` [`str`, `str`]]
            A list of dicts representing bucket objects.
        """
        objects = []
        for cam in location.cameras:
            if cam.online:
                prefix = cam.name
                logger.info(
                    "Listing objects for:",
                    location=location.name,
                    prefix=prefix,
                )
                try:
                    client: S3Client = self._clients[location.name]
                    one_load = await client.async_list_objects(prefix=prefix)
                    objects.extend(one_load)
                    logger.info("Found:", num_objects=len(one_load))
                except Exception as e:
                    logger.error(e)
        return objects

    async def filter_convert_store_objects(
        self, objects: list[dict[str, str]], location: Location
    ) -> None:
        locname = location.name

        metadata_objs = [o for o in objects if "metadata.json" in o["key"]]
        n_report_objs = [o for o in objects if "night_report" in o["key"]]

        event_objs = [
            o
            for o in objects
            if "metadata.json" not in o["key"] and "night_report" not in o["key"]
        ]

        self._nr_metadata[locname] = await objects_to_ngt_report_data(n_report_objs)
        async for events_batch in objects_to_events(event_objs):
            await self.store_events(events_batch, locname)
        await self.compress_events()
        self._temp_events = {}
        await self.compress_events()
        self._temp_events = {}

        await self.download_and_store_metadata(locname, metadata_objs)

    async def compress_events(self) -> None:
        for storage_key, events in self._temp_events.items():
            compressed = zlib.compress(pickle.dumps(events))
            if storage_key in self._compressed_events:
                self._compressed_events[storage_key] += compressed
            else:
                self._compressed_events[storage_key] = compressed

    async def store_events(self, events: list[Event], locname: str) -> None:
        for event in events:
            loc_cam = f"{locname}/{event.camera_name}"

            if loc_cam not in self._temp_events:
                self._temp_events[loc_cam] = []
            self._temp_events[loc_cam].append(event)

            seq_num = event.seq_num
            if isinstance(seq_num, str):
                seq_num = 1
            self.add_to_calendar(loc_cam, event.day_obs, seq_num)

    def add_to_calendar(self, loc_cam: str, date_str: str, seq_num: int) -> None:
        year_str, month_str, day_str = date_str.split("-")
        year, month, day = (int(year_str), int(month_str), int(day_str))
        if loc_cam not in self._calendar:
            self._calendar[loc_cam] = {}
        if year not in self._calendar[loc_cam]:
            self._calendar[loc_cam][year] = {}
        if month not in self._calendar[loc_cam][year]:
            self._calendar[loc_cam][year][month] = {}
        if self._calendar[loc_cam][year][month].get(day, 0) <= seq_num:
            self._calendar[loc_cam][year][month][day] = seq_num

    async def download_and_store_metadata(
        self, locname: str, metadata_objs: list[dict[str, str]]
    ) -> None:
        # metadata is downloaded and stored against its loc/cam/date
        # for efficient retrieval
        logger.info("Fetching metadata for:", locname=locname)
        t = time()
        for md_obj in metadata_objs:
            key = md_obj.get("key")
            if not key:
                continue
            storage_name = locname + "/" + key.split("/metadata")[0]
            _, cam_name, date_str = storage_name.split("/")
            loc_cam = f"{locname}/{cam_name}"
            self.add_to_calendar(loc_cam, date_str, 0)

            client = self._clients[locname]
            md = await client.async_get_object(key)
            if not md:
                logger.info("Missing metadata for:", md_obj=md_obj)
                continue
            compressed_md = zlib.compress(pickle.dumps(md))
            self._metadata[storage_name] = compressed_md
        dur = time() - t
        logger.info("Metatdata fetch took", locname=locname, dur=dur)

    async def get_night_report_payload(
        self, location: Location, camera: Camera, day_obs: date
    ) -> NightReport:
        """Returns a NightReport for the camera and date.

        Parameters
        ----------
        camera : `Camera`
            The given Camera.
        obs_date : `date`
            The given date.

        Returns
        -------
        report : `NightReport`
            A NightReport containing a list of Night Report Data and text
            metadata.
        """
        nr_data = await self._get_night_report_data(location, camera, day_obs)
        text_reports = [r for r in nr_data if r.group == "metadata"]
        report: NightReport = NightReport()
        if text_reports:
            text_report = text_reports[0]
            key = text_report.key
            client = self._clients[location.name]
            text_obj = await client.async_get_object(key)
            report.text = text_obj
            nr_data.remove(text_report)
        if nr_data:
            report.plots = nr_data
        return report

    async def _get_night_report_data(
        self, location: Location, camera: Camera, day_obs: date
    ) -> list[NightReportData]:
        date_str = day_obs.isoformat()
        report = []
        if location.name in self._nr_metadata:
            report = [
                nr
                for nr in self._nr_metadata[location.name]
                if nr.camera == camera.name and nr.day_obs == date_str
            ]
        return report

    async def night_report_exists_for(
        self, location: Location, camera: Camera, day_obs: date
    ) -> bool:
        nr_data = await self._get_night_report_data(location, camera, day_obs)
        if nr_data:
            return True
        else:
            return False

    async def get_events_for_date(
        self, location: Location, camera: Camera, a_date: date
    ) -> list[Event]:
        loc_cam = f"{location.name}/{camera.name}"
        date_str = a_date.isoformat()
        to_decompress = self._compressed_events.get(loc_cam, None)
        if to_decompress is None:
            return []
        events: list[Event] = pickle.loads(zlib.decompress(to_decompress))
        events = [e for e in events if e.day_obs == date_str]
        return events

    async def get_channel_data_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[int, dict[str, dict]]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        channel_data = await make_table_from_event_list(events, camera.seq_channels())
        return channel_data

    async def get_per_day_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, dict[str, dict]]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        chan_names = [c.name for c in camera.pd_channels()]
        per_day_lists = [e for e in events if e.channel_name in chan_names]
        if not per_day_lists:
            return {}
        per_day = {}
        for event in per_day_lists:
            per_day[event.channel_name] = event.__dict__
        return per_day

    async def get_metadata_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, Any]:
        cam_name = camera.name
        if camera.metadata_from:
            cam_name = camera.metadata_from
        loc_cam_date = f"{location.name}/{cam_name}/{day_obs}"
        compressed = self._metadata.get(loc_cam_date, None)
        if compressed is None:
            return {}
        return pickle.loads(zlib.decompress(compressed))

    async def get_most_recent_day(
        self, location: Location, camera: Camera
    ) -> date | None:
        loc_cam = f"{location.name}/{camera.name}"
        calendar = self._calendar.get(loc_cam)
        if not calendar:
            return None
        year = max(calendar.keys())
        month = max(calendar[year].keys())
        day = max(calendar[year][month].keys())
        return date(year, month, day)

    async def get_most_recent_events(
        self, location: Location, camera: Camera
    ) -> list[Event]:
        loc_cam = f"{location.name}/{camera.name}"
        day_obs = await self.get_most_recent_day(location, camera)
        if not day_obs:
            return []
        compressed = self._compressed_events.get(loc_cam, None)
        if compressed is None:
            return []
        events = pickle.loads(zlib.decompress(compressed))
        date_str = day_obs.isoformat()
        return [e for e in events if e.day_obs == date_str]

    async def get_most_recent_event(
        self, location: Location, camera: Camera, channel: Channel
    ) -> Event | None:
        loc_cam = f"{location.name}/{camera.name}"
        compressed = self._compressed_events.get(loc_cam, None)
        if compressed is None:
            return None
        events = pickle.loads(zlib.decompress(compressed))
        events = [event for event in events if event.channel_name == channel.name]
        if not events:
            return None
        return max(events)

    async def get_next_prev_event(
        self, location: Location, camera: Camera, event: Event
    ) -> tuple[dict | None, ...]:
        day_obs = event.day_obs_date()
        table = await self.get_channel_data_for_date(location, camera, day_obs)
        nxt_prv = await get_next_previous_from_table(table, event)
        return nxt_prv

    async def get_most_recent_channel_data(
        self, location: Location, camera: Camera
    ) -> dict[int, dict[str, dict]]:
        day = await self.get_most_recent_day(location, camera)
        if not day:
            return {}
        data = await self.get_channel_data_for_date(location, camera, day)
        return data

    async def get_camera_calendar(
        self, location: Location, camera: Camera
    ) -> dict[int, dict[int, dict[int, int]]]:
        """Returns a dict representing a calendar for the given Camera

        Provides a list of tuples for (days and max seq_num of Events), within
        a dict of months, within a dict keyed by year for the given Camera.

        Parameters
        ----------
        camera : `Camera`
            The given Camera object.

        Returns
        -------
        years : `dict` [`int`, `dict` [`int`, `dict` [`int`, `int` | `str`]]]
            A data structure for the view to iterate over with years, months,
            days and num. of events for that day for the given Camera.

        """
        loc_cam = f"{location.name}/{camera.name}"
        return self._calendar.get(loc_cam, {})
