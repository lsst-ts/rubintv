import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import structlog

from rubintv.background.background_helpers import get_metadata_obj
from rubintv.handlers.websocket_notifiers import notify_all_status_change
from rubintv.models.models import (
    Camera,
    Channel,
    Event,
    Location,
    NightReport,
    NightReportPayload,
    get_current_day_obs,
)
from rubintv.models.models_helpers import (
    make_table_from_event_list,
    objects_to_events,
    objects_to_ngt_reports,
)
from rubintv.s3client import S3Client


class HistoricalPoller:
    """Provide a cache of the historical data.

    Provides a cache of the historical data which updates when the day rolls
    over.
    """

    _clients: dict[str, S3Client] = {}

    _metadata: dict[str, dict] = {}
    _events: dict[str, list[Event]] = {}
    _nr_metadata: dict[str, list[NightReport]] = {}

    # {loc_cam: {year: {months: {days : max_seq }}}}
    _calendar: dict[str, dict[int, dict[int, dict[int, int]]]] = {}

    # polling period in seconds
    CHECK_NEW_DAY_PERIOD = 60

    def __init__(self, locations: list[Location]) -> None:
        self._locations = locations
        self._clients = {
            location.name: S3Client(location.bucket_name)
            for location in locations
        }

        self._have_downloaded = False
        self._last_reload = get_current_day_obs()

        self.cam_year_rgx = re.compile(r"(\w+)\/([\d]{4})-[\d]{2}-[\d]{2}")

    async def is_busy(self) -> bool:
        return not self._have_downloaded

    async def check_for_new_day(self) -> None:
        logger = structlog.get_logger(__name__)
        try:
            while True:
                if (
                    not self._have_downloaded
                    or self._last_reload > get_current_day_obs()
                ):
                    for location in self._locations:
                        await self._refresh_location_store(location)

                    self._last_reload = get_current_day_obs()
                    self._have_downloaded = True
                    logger.info("Completed historical")
                    await notify_all_status_change(historical_busy=False)
                else:
                    await asyncio.sleep(self.CHECK_NEW_DAY_PERIOD)
        except Exception as e:
            logger.error(e)

    async def _refresh_location_store(self, location: Location) -> None:
        # handle blocking call in async code
        logger = structlog.get_logger(__name__)
        executor = ThreadPoolExecutor(max_workers=3)
        loop = asyncio.get_event_loop()
        try:
            up_to_date_objects = await loop.run_in_executor(
                executor, self._get_objects, location
            )
            await self.filter_convert_store_objects(
                up_to_date_objects, location
            )
        except Exception as e:
            logger.error(e)

    def _get_objects(self, location: Location) -> list[dict[str, str]]:
        """Downloads objects from the bucket for each online camera for the
        location. Is a blocking call so is called via run_in_executor

        Returns
        -------
        objects :  `list` [`dict` [`str`, `str`]]
            A list of dicts representing bucket objects.
        """
        logger = structlog.get_logger(__name__)

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
                    one_load = self._clients[location.name].list_objects(
                        prefix=prefix
                    )
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
            if o not in metadata_objs and o not in n_report_objs
        ]

        await self.download_and_store_metadata(locname, metadata_objs)

        self._nr_metadata[locname] = await objects_to_ngt_reports(
            n_report_objs
        )
        events = await objects_to_events(event_objs)
        await self.store_events(events, locname)

    async def store_events(self, events: list[Event], locname: str) -> None:
        for event in events:
            storage_name = await self.storage_name_for_event(event, locname)
            if storage_name not in self._events:
                self._events[storage_name] = []
            self._events[storage_name].append(event)

            if isinstance(event.seq_num, str):
                continue
            year_str, month_str, day_str = event.day_obs.split("-")
            year, month, day = (int(year_str), int(month_str), int(day_str))
            loc_cam = f"{locname}/{event.camera_name}"
            if loc_cam not in self._calendar:
                self._calendar[loc_cam] = {}
            if year not in self._calendar[loc_cam]:
                self._calendar[loc_cam][year] = {}
            if month not in self._calendar[loc_cam][year]:
                self._calendar[loc_cam][year][month] = {}
            if (
                self._calendar[loc_cam][year][month].get(day, 0)
                <= event.seq_num
            ):
                self._calendar[loc_cam][year][month][day] = event.seq_num

    async def storage_name_for_event(self, event: Event, locname: str) -> str:
        return f"{locname}/{event.camera_name}"

    async def download_and_store_metadata(
        self, locname: str, metadata_objs: list[dict[str, str]]
    ) -> None:
        # metadata is downloaded and stored against it's loc/cam/date
        # for efficient retrieval
        logger = structlog.get_logger(__name__)
        for md_obj in metadata_objs:
            key = md_obj.get("key")
            if not key:
                continue
            storage_name = locname + "/" + key.split("/metadata")[0]
            md = await get_metadata_obj(key, self._clients[locname])
            if not md:
                logger.info("Missing metadata for:", md_obj=md_obj)
                continue
            self._metadata[storage_name] = md

    async def get_night_report_payload(
        self, location: Location, camera: Camera, day_obs: date
    ) -> NightReportPayload:
        """Returns a dict containing a list of Night Reports for
        the camera and date and a text metadata dict. Both values are
        optional (see `NightReportPayload`).

        Parameters
        ----------
        camera : `Camera`
            The given Camera.
        obs_date : `date`
            The given date.

        Returns
        -------
        report : NightReportPayload:
            A dict containing a list of Night Report objects and text metadata.
        """
        nr_objs = await self._get_night_report(location, camera, day_obs)
        text_reports = [r for r in nr_objs if r.group == "metadata"]
        report: NightReportPayload = {}
        if text_reports:
            text_report = text_reports[0]
            key = text_report.key
            client = self._clients[location.name]
            text_obj = await get_metadata_obj(key, client)
            report["text"] = text_obj
            nr_objs.remove(text_report)
        if nr_objs:
            report["plots"] = nr_objs
        return report

    async def _get_night_report(
        self, location: Location, camera: Camera, day_obs: date
    ) -> list[NightReport]:
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
        nr_objs = await self._get_night_report(location, camera, day_obs)
        if nr_objs:
            return True
        else:
            return False

    async def get_events_for_date(
        self, location: Location, camera: Camera, a_date: date
    ) -> list[Event]:
        loc_cam = f"{location.name}/{camera.name}"
        date_str = a_date.isoformat()
        events = [e for e in self._events[loc_cam] if e.day_obs == date_str]
        return events

    async def get_channel_data_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[int, dict[str, dict]]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        channel_data = await make_table_from_event_list(
            events, camera.seq_channels()
        )
        return channel_data

    async def get_per_day_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, Event]:
        events = await self.get_events_for_date(location, camera, day_obs)
        if not events:
            return {}
        chan_names = [c.name for c in camera.pd_channels()]
        per_day_lists = [e for e in events if e.channel_name in chan_names]
        if not per_day_lists:
            return {}
        per_day = {}
        for event in per_day_lists:
            per_day[event.channel_name] = event
        return per_day

    async def get_metadata_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> dict[str, dict]:
        loc_cam_date = f"{location.name}/{camera.name}/{day_obs}"
        return self._metadata.get(loc_cam_date, {})

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
        date_str = day_obs.isoformat()
        return [e for e in self._events[loc_cam] if e.day_obs == date_str]

    async def get_most_recent_event(
        self, location: Location, camera: Camera, channel: Channel
    ) -> Event | None:
        events = [
            event
            for event in await self.get_most_recent_events(location, camera)
            if event.channel_name == channel.name
        ]
        if not events:
            return None
        return events.pop()

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
