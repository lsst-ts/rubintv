import asyncio
from datetime import date
from time import time

from lsst.ts.rubintv.background.background_helpers import get_next_previous_from_table
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import (
    notify_all_status_change,
    notify_ws_clients,
)
from lsst.ts.rubintv.models.models import (
    Camera,
    Channel,
    Event,
    Location,
    NightReport,
    NightReportData,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import ServiceTypes as Service
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import (
    date_str_to_date,
    daterange,
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

    def __init__(
        self,
        locations: list[Location],
        test_mode: bool = False,
        prefix_extra: str = "",
        test_date_start: str | None = None,
        test_date_end: str | None = None,
    ) -> None:
        self._clients: dict[str, S3Client] = {}

        self._metadata_refs: dict[str, set[str]] = {}
        # Structure: {loc_cam: {date_str}}

        self._structured_events: dict[str, dict[str, dict[str, set[int | str]]]] = {}
        # Structure: {loc_cam: {date_str: {
        #  channel_name: {seq_num1, seq_num2, ...}}}}

        self._channel_default_extensions: dict[str, str] = {}
        # Structure: {f"{loc_cam}/{date_str}/{channel_name}": "default_ext"}

        self._extension_exceptions: dict[str, dict[int | str, str]] = {}
        # Structure: {f"{loc_cam}/{date_str}/{channel_name}":
        #   {seq_num: "different_ext"}}

        self._nr_metadata: dict[str, list[NightReportData]] = {}
        self._calendar: dict[str, dict[int, dict[int, dict[int, int]]]] = {}
        self._locations = locations
        self._clients = {
            location.name: S3Client(
                location.profile_name, location.bucket_name, location.endpoint_url
            )
            for location in locations
        }

        self._have_downloaded = False
        self._last_reload = get_current_day_obs()

        self.test_mode = test_mode
        self.test_date_start: date | None = None
        self.test_date_end: date | None = None
        if test_date_start:
            self.test_date_start = date_str_to_date(test_date_start)
        if test_date_end:
            self.test_date_end = date_str_to_date(test_date_end)
        self.prefix_extra = prefix_extra

    async def clear_all_data(self) -> None:
        self._have_downloaded = False
        self._metadata_refs = {}
        self._structured_events = {}
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
                    # Let the clients know the day has changed
                    await self.notify_clients_of_day_change()

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
        except Exception:
            # log error with traceback
            logger.error("Error in check_for_new_day", exc_info=True)

    async def notify_clients_of_day_change(self) -> None:
        """Notify the clients that the day has changed."""
        for loc in self._locations:
            for cam in loc.cameras:
                if cam.online:
                    await notify_ws_clients(
                        Service.CALENDAR,
                        MessageType.DAY_CHANGE,
                        f"{loc.name}/{cam.name}",
                        "from historical",
                    )

    async def _refresh_location_store(self, location: Location) -> None:
        try:
            up_to_date_objects = await self._get_objects_for_location(location)
            await self.filter_convert_store_objects(up_to_date_objects, location)
        except Exception as e:
            logger.error(e)

    async def _get_objects_for_location(
        self, location: Location
    ) -> list[dict[str, str]]:
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
                prefixes = []
                if self.test_date_start and self.test_date_end:
                    for aDate in daterange(
                        self.test_date_start,
                        self.test_date_end,
                    ):
                        date_str = aDate.isoformat()
                        prefixes.append(f"{cam.name}/{date_str}/{self.prefix_extra}")
                else:
                    prefixes.append(cam.name + "/" + self.prefix_extra)

                for prefix in prefixes:
                    try:
                        objects.extend(
                            await self._get_objects_for_prefix(location, prefix)
                        )
                    except Exception as e:
                        logger.error(e)
        return objects

    async def _get_objects_for_prefix(
        self, location: Location, prefix: str
    ) -> list[dict[str, str]]:
        """Downloads objects from the bucket for the given prefix.

        Parameters
        ----------
        location : `Location`
            The location to get objects for.
        prefix : `str`
            The prefix to filter objects by.

        Returns
        -------
        objects :  `list` [`dict` [`str`, `str`]]
            A list of dicts representing bucket objects.
        """
        logger.info(
            "Fetching objects for prefix:",
            location=location.name,
            prefix=prefix,
        )
        client: S3Client = self._clients[location.name]
        objects = await client.async_list_objects(prefix=prefix)
        logger.info("Found:", num_objects=len(objects), prefix=prefix)
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
            await self.store_events_structured(events_batch, locname)

        await self.store_metadata_dates(locname, metadata_objs)

    async def store_events_structured(self, events: list[Event], locname: str) -> None:
        """Highly optimized event storage with extension deduplication."""

        # Group events by channel-date to analyze extension patterns
        channel_date_groups: dict[str, list[Event]] = {}

        for event in events:
            loc_cam = f"{locname}/{event.camera_name}"
            channel_date_key = f"{loc_cam}/{event.day_obs}/{event.channel_name}"

            if channel_date_key not in channel_date_groups:
                channel_date_groups[channel_date_key] = []
            channel_date_groups[channel_date_key].append(event)

        # Process each channel-date group
        for channel_date_key, group_events in channel_date_groups.items():
            await self._store_channel_date_group(channel_date_key, group_events)

    async def _store_channel_date_group(
        self, channel_date_key: str, events: list[Event]
    ) -> None:
        """Store events for a specific channel-date, optimizing extension
        storage."""

        # Parse the channel_date_key
        parts = channel_date_key.split("/")
        locname = parts[0]
        camera_name = parts[1]
        date_str = parts[2]
        channel_name = parts[3]
        loc_cam = f"{locname}/{camera_name}"

        # Initialize nested structure
        if loc_cam not in self._structured_events:
            self._structured_events[loc_cam] = {}
        if date_str not in self._structured_events[loc_cam]:
            self._structured_events[loc_cam][date_str] = {}
        if channel_name not in self._structured_events[loc_cam][date_str]:
            self._structured_events[loc_cam][date_str][channel_name] = set()

        # Analyze extensions to find the most common one
        extension_counts: dict[str, int] = {}
        event_extensions: dict[int | str, str] = {}

        for event in events:
            seq_num = event.seq_num
            ext = event.ext

            # Track extension frequency
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
            event_extensions[seq_num] = ext

            # Store seq_num (we'll determine how to store extension below)
            self._structured_events[loc_cam][date_str][channel_name].add(seq_num)

            # Update calendar
            self.add_to_calendar(loc_cam, date_str, event.seq_num_force_int())

        # Determine the default extension (most common)
        if extension_counts:
            default_ext = max(extension_counts, key=lambda ext: extension_counts[ext])
            self._channel_default_extensions[channel_date_key] = default_ext

            # Store only the exceptions
            exceptions = {
                seq_num: ext
                for seq_num, ext in event_extensions.items()
                if ext != default_ext
            }

            if exceptions:
                self._extension_exceptions[channel_date_key] = exceptions

    def get_extension_for_event(
        self, loc_cam: str, date_str: str, channel_name: str, seq_num: int | str
    ) -> str:
        """Get the extension for a specific event, using default and
        exceptions pattern."""
        channel_date_key = f"{loc_cam}/{date_str}/{channel_name}"

        # Check if there's an exception for this seq_num
        if channel_date_key in self._extension_exceptions:
            exceptions = self._extension_exceptions[channel_date_key]
            if seq_num in exceptions:
                return exceptions[seq_num]

        # Return the default extension
        return self._channel_default_extensions.get(channel_date_key, "jpg")

    def reconstruct_filename(
        self, camera_name: str, channel_name: str, seq_num: int | str, ext: str
    ) -> str:
        """Reconstruct filename from components."""
        if isinstance(seq_num, str):
            base_name = f"{camera_name}_{channel_name}_{seq_num}"
        else:
            base_name = f"{camera_name}_{channel_name}_{seq_num:06d}"
        return f"{base_name}.{ext}"

    async def get_events_for_date_structured(
        self, location: Location, camera: Camera, a_date: date
    ) -> list[Event]:
        """Efficient event retrieval using optimized structure."""
        loc_cam = f"{location.name}/{camera.name}"
        date_str = a_date.isoformat()

        if (
            loc_cam not in self._structured_events
            or date_str not in self._structured_events[loc_cam]
        ):
            return []

        events = []
        for channel_name, seq_data in self._structured_events[loc_cam][
            date_str
        ].items():
            for seq_num in seq_data:
                ext = self.get_extension_for_event(
                    loc_cam, date_str, channel_name, seq_num
                )

                # Reconstruct filename and key
                filename = self.reconstruct_filename(
                    camera.name, channel_name, seq_num, ext
                )
                if isinstance(seq_num, str):
                    # seq_num is 'final' or similar non-integer
                    key = (
                        f"{camera.name}/{date_str}/{channel_name}/{seq_num}/{filename}"
                    )
                else:
                    key = f"{camera.name}/{date_str}/{channel_name}/{seq_num:06d}/{filename}"
                events.append(Event(key=key))

        return events

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

    async def store_metadata_dates(
        self, locname: str, metadata_objs: list[dict[str, str]]
    ) -> None:

        logger.info("Fetching metadata for:", locname=locname)
        for md_obj in metadata_objs:
            key = md_obj.get("key")
            if not key:
                continue
            storage_name = locname + "/" + key.split("/metadata")[0]
            _, cam_name, date_str = storage_name.split("/")
            loc_cam = f"{locname}/{cam_name}"
            self._metadata_refs.setdefault(loc_cam, set()).add(date_str)
            self.add_to_calendar(loc_cam, date_str, 0)

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
                if nr.camera_name == camera.name and nr.day_obs == date_str
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
        events_for_date = await self.get_events_for_date_structured(
            location, camera, a_date
        )
        return events_for_date

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

    async def check_for_metadata_for_date(
        self, location: Location, camera: Camera, day_obs: date
    ) -> bool:
        date_str = day_obs.isoformat()
        loc_cam = f"{location.name}/{camera.name}"
        if loc_cam in self._metadata_refs and date_str in self._metadata_refs[loc_cam]:
            return True
        return False

    def flatten_calendar(self, location: Location, camera: Camera) -> dict[str, int]:
        """Flatten the calendar for a given location and camera.

        Returns a dict with keys as date strings and values as the number of
        events for that date.
        """
        loc_cam = f"{location.name}/{camera.name}"
        calendar = self._calendar.get(loc_cam, {})
        flat_calendar = {}
        for year in calendar:
            for month in calendar[year]:
                for day, seq_num in calendar[year][month].items():
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    flat_calendar[date_str] = seq_num
        return flat_calendar

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
        most_recent = date(year, month, day)
        if most_recent != get_current_day_obs():
            return most_recent
        # check there is more than one day in the calendar
        # if there is only one day, return None
        flat_calendar = self.flatten_calendar(location, camera)
        num_days = len(flat_calendar)
        if num_days <= 1:
            return None
        second_most_recent = sorted(flat_calendar.keys())[-2]
        return date_str_to_date(second_most_recent)

    async def get_most_recent_events(
        self, location: Location, camera: Camera
    ) -> list[Event]:
        day_obs = await self.get_most_recent_day(location, camera)
        if not day_obs:
            return []
        events_for_date = await self.get_events_for_date_structured(
            location, camera, day_obs
        )
        return events_for_date

    async def get_most_recent_event(
        self, location: Location, camera: Camera, channel: Channel
    ) -> Event | None:
        events = await self.get_most_recent_events(location, camera)
        events = [e for e in events if e.channel_name == channel.name]
        if not events:
            return None
        return max(events)

    def unarchive_events(self, archived_events: list[str]) -> list[Event]:
        return [Event(key=e) for e in archived_events]

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

    async def get_all_channel_names_for_date_and_seq_num(
        self, location: Location, camera: Camera, date: str, seq_num: int
    ) -> list[str]:
        """Returns a list of Events for the given date and seq_num.

        Parameters
        ----------
        camera : `Camera`
            The given Camera.
        date : `str`
            The given date.
        seq_num : `int`
            The given sequence number.

        Returns
        -------
        chan_names : `list` [`str`]
            A list of channel names for the given date and seq_num.
        """
        loc_cam = f"{location.name}/{camera.name}"

        if (
            loc_cam not in self._structured_events
            or date not in self._structured_events[loc_cam]
        ):
            return []

        channel_names = []
        for channel_name, seq_data in self._structured_events[loc_cam][date].items():
            if seq_num in seq_data:
                channel_names.append(channel_name)

        return channel_names
