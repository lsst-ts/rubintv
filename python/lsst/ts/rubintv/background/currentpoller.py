from asyncio import sleep
from time import time
from typing import AsyncGenerator

from lsst.ts.rubintv.background.background_helpers import get_next_previous_from_table
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import notify_ws_clients
from lsst.ts.rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReport,
    NightReportData,
)
from lsst.ts.rubintv.models.models import ServiceMessageTypes as MessageType
from lsst.ts.rubintv.models.models import get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import (
    all_objects_to_events,
    make_table_from_event_list,
    objects_to_ngt_report_data,
)
from lsst.ts.rubintv.s3client import S3Client

logger = rubintv_logger()


class CurrentPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    # min time between polls
    MIN_INTERVAL = 1

    def __init__(self, locations: list[Location], test_mode: bool = False) -> None:
        self._s3clients: dict[str, S3Client] = {}
        self._objects: dict[str, list] = {}
        self._events: dict[str, list[Event]] = {}
        self._metadata: dict[str, dict] = {}
        self._table: dict[str, dict[int, dict[str, dict]]] = {}
        self._per_day: dict[str, dict[str, dict]] = {}
        self._yesterday_prefixes: dict[str, list[str]] = {}
        self._most_recent_events: dict[str, Event] = {}
        self._nr_metadata: dict[str, NightReportData] = {}
        self._night_reports: dict[str, NightReport] = {}
        self.test_mode = test_mode
        self._test_iterations = 1

        self.completed_first_poll = False
        self.locations = locations
        self._current_day_obs = get_current_day_obs()
        for location in locations:
            self._s3clients[location.name] = S3Client(
                location.profile_name, location.bucket_name
            )

    async def clear_todays_data(self) -> None:
        self._objects = {}
        self._events = {}
        self._metadata = {}
        self._table = {}
        self._per_day = {}
        self._most_recent_events = {}
        self._nr_metadata = {}
        self._night_reports = {}

    async def check_for_empty_per_day_channels(self) -> None:
        """Creates a store of channel prefixes for per-day data that's not
        been received over the course of a day's polling. The prefixes use the
        date that's been rolled over from, i.e. yesterday's date, to continue
        to look for that data into the new day.
        """
        for location in self.locations:
            # clear out yesterday's stash
            self._yesterday_prefixes[location.name] = []
            for camera in location.cameras:
                if not camera.online:
                    continue
                if not (chans := camera.pd_channels()):
                    continue
                stored_per_day = await self.get_current_per_day_data(
                    location.name, camera
                )
                missing_chans = [
                    chan for chan in chans if chan.name not in stored_per_day
                ]
                loc_prefixes = self._yesterday_prefixes[location.name]
                for chan in missing_chans:
                    prefix = f"{camera.name}/{self._current_day_obs}/{chan.name}"
                    loc_prefixes.append(prefix)

    async def poll_buckets_for_todays_data(self, test_day: str = "") -> None:
        while True:
            timer_start = time()
            try:
                if self._current_day_obs != get_current_day_obs():
                    await self.check_for_empty_per_day_channels()
                    await self.clear_todays_data()
                day_obs = self._current_day_obs = get_current_day_obs()

                for location in self.locations:
                    client = self._s3clients[location.name]
                    for camera in location.cameras:
                        if not camera.online:
                            continue

                        prefix = f"{camera.name}/{day_obs}"
                        if test_day:
                            prefix = f"{camera.name}/{test_day}"

                        objects = await client.async_list_objects(prefix)
                        if objects:
                            loc_cam = self._get_loc_cam(location.name, camera)
                            objects = await self.sieve_out_metadata(
                                objects, prefix, location, camera
                            )
                            objects = await self.sieve_out_night_reports(
                                objects, location, camera
                            )
                            await self.process_channel_objects(objects, loc_cam, camera)

                    await self.poll_for_yesterdays_per_day(location)

                self.completed_first_poll = True

                if self.test_mode:
                    self._test_iterations -= 1
                    if self._test_iterations <= 0:
                        break

                elapsed = time() - timer_start
                logger.info("Current - time taken:", elapsed=elapsed)
                if elapsed < self.MIN_INTERVAL:
                    await sleep(self.MIN_INTERVAL - elapsed)

            except Exception:
                logger.exception("Caught exception during poll for data")

    async def poll_for_yesterdays_per_day(self, location: Location) -> None:
        """Uses the store of prefixes for yesterday's missing per-day data to
        poll for new objects that have maybe been delayed in processing (this
        will mainly be movies) and didn't appear in the bucket before the day
        rolled over.
        Multiple objects will be ignored except for the most recent.
        If an object is found in the bucket, the current page is notified.
        Note: This does not effect historical pages.


        Parameters
        ----------
        location : Location
            A given location.
        """
        client = self._s3clients[location.name]
        found = []
        for prefix in self._yesterday_prefixes.get(location.name, []):
            objects = await client.async_list_objects(prefix)
            if objects:
                found.append(prefix)
                events = await all_objects_to_events(objects)
                pd_data = {e.channel_name: e.__dict__ for e in events}
                cam_name = prefix.split("/")[0]
                loc_cam = f"{location.name}/{cam_name}"
                logger.info(
                    "Found yesterday's per day data:", loc_cam=loc_cam, pd_data=pd_data
                )
                await notify_ws_clients(
                    "camera", MessageType.CAMERA_PD_BACKDATED, loc_cam, pd_data
                )
        for prefix in found:
            self._yesterday_prefixes[location.name].remove(prefix)

    async def process_channel_objects(
        self, objects: list[dict[str, str]], loc_cam: str, camera: Camera
    ) -> None:
        if objects and (
            loc_cam not in self._objects or objects != self._objects[loc_cam]
        ):
            self._objects[loc_cam] = objects
            events = await all_objects_to_events(objects)
            self._events[loc_cam] = events
            await self.update_channel_events(events, loc_cam, camera)

            pd_data = await self.make_per_day_data(camera, events)
            self._per_day[loc_cam] = pd_data
            await notify_ws_clients(
                "camera", MessageType.CAMERA_PER_DAY, loc_cam, pd_data
            )

            table = await self.make_channel_table(camera, events)
            self._table[loc_cam] = table
            logger.info(
                "Current - updating table for:",
                loc_cam=loc_cam,
                num_seqs=len(table),
                max_seq=max(table) if table else -1,
            )
            await notify_ws_clients("camera", MessageType.CAMERA_TABLE, loc_cam, table)

            # clear all relevant prefixes from the store looking for
            # yesterday's per day updates

            loc = loc_cam.split("/")[0]
            prefixes = self._yesterday_prefixes.get(loc, [])
            new_prefixes = [
                prefix for prefix in prefixes if not prefix.startswith(camera.name)
            ]
            self._yesterday_prefixes[loc] = new_prefixes

    async def update_channel_events(
        self, events: list[Event], loc_cam: str, camera: Camera
    ) -> None:
        if not events:
            return
        for chan in camera.channels:
            ch_events = [e for e in events if e.channel_name == chan.name]
            if not ch_events:
                continue
            # get most recent event for this channel
            current_event = ch_events.pop()
            chan_lookup = f"{loc_cam}/{chan.name}"
            if (
                chan_lookup not in self._most_recent_events
                or self._most_recent_events[chan_lookup] != current_event
            ):
                self._most_recent_events[chan_lookup] = current_event
                await notify_ws_clients(
                    "channel",
                    MessageType.CHANNEL_EVENT,
                    chan_lookup,
                    current_event.__dict__,
                )

    async def sieve_out_metadata(
        self,
        objects: list[dict[str, str]],
        prefix: str,
        location: Location,
        camera: Camera,
    ) -> list[dict[str, str]]:
        try:
            md_obj, objects = await self.filter_camera_metadata_object(objects)
        except ValueError:
            logger.error(f"More than one metadata file found for {prefix}")
        if md_obj:
            await self.process_metadata_file(md_obj, location, camera)
        return objects

    async def filter_camera_metadata_object(
        self, objects: list[dict[str, str]]
    ) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
        """Given a list of objects, seperates out the camera metadata dict
        object, if it exists, having made sure there is only one metadata file
        for that day.

        Parameters
        ----------
        objects : `list` [`dict`[`str`, `str`]]
            A list of dicts that represent s3 objects comprising `"key"` and
            `"hash"` keys.

        Returns
        -------
        `tuple` [`dict` [`str`, `str`] | `None`, `list` [`dict` [`str`,`str`]]]
            A tuple for unpacking with the dict representing the metadata json
            file, or None if there isn't one and the remaining list of objects.

        Raises
        ------
        `ValueError`
            If there is more than one metadata file, a ValueError is raised.
        """
        md_objs = [o for o in objects if o["key"].endswith("metadata.json")]
        if len(md_objs) > 1:
            raise ValueError
        md_obj = None
        to_return = objects
        if md_objs != []:
            md_obj = md_objs[0]
            to_return = [o for o in objects if o != md_obj]
        return (md_obj, to_return)

    async def process_metadata_file(
        self, md_obj: dict[str, str], location: Location, camera: Camera
    ) -> None:
        loc_cam = self._get_loc_cam(location.name, camera)
        md_key = md_obj["key"]
        client = self._s3clients[location.name]
        data = await client.async_get_object(md_key)
        if data and (loc_cam not in self._metadata or data != self._metadata[loc_cam]):
            self._metadata[loc_cam] = data
            logger.info("Current - metadata file processed for:", loc_cam=loc_cam)
            # some channels e.g. Star Trackers share the same metadata file.
            # If it changes, the websocket clients listening to those cameras
            # need to be notified too.
            to_notify = [camera]
            to_notify.extend(
                c for c in location.cameras if c.metadata_from == camera.name
            )
            for cam in to_notify:
                loc_cam = self._get_loc_cam(location.name, cam)
                await notify_ws_clients(
                    "camera", MessageType.CAMERA_METADATA, loc_cam, data
                )

    async def sieve_out_night_reports(
        self, objects: list[dict[str, str]], location: Location, camera: Camera
    ) -> list[dict[str, str]]:
        loc_cam = self._get_loc_cam(location.name, camera)
        report_objs, objects = await self.filter_night_report_objects(objects)
        if report_objs:
            if not self.night_report_exists(location.name, camera.name):
                await notify_ws_clients(
                    "camera",
                    MessageType.CAMERA_PER_DAY,
                    loc_cam,
                    {"nightReportExists": True},
                )
                await self.process_night_report_objects(report_objs, location, camera)
        return objects

    async def filter_night_report_objects(
        self, objects: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        report_objs = [o for o in objects if "night_report" in o["key"]]
        filtered = [o for o in objects if o not in report_objs]
        return (report_objs, filtered)

    async def process_night_report_objects(
        self, report_objs: list[dict[str, str]], location: Location, camera: Camera
    ) -> None:
        loc_cam = self._get_loc_cam(location.name, camera)
        prev_nr = await self.get_current_night_report(location.name, camera.name)
        night_report = NightReport()

        reports_data = await objects_to_ngt_report_data(report_objs)
        metadata_files = [r for r in reports_data if r.group == "metadata"]
        if len(metadata_files) > 1:
            logger.error("More than one night report metadata file for {loc_cam}")
        if metadata_files:
            metadata_file = metadata_files[0]
            if (
                loc_cam not in self._nr_metadata
                or self._nr_metadata[loc_cam] != metadata_file
            ):
                client = self._s3clients[location.name]
                text = await client.async_get_object(metadata_file.key)
                night_report.text = text
                self._nr_metadata[loc_cam] = metadata_file
            else:
                night_report.text = prev_nr.text

            for mf in metadata_files:
                reports_data.remove(mf)

        night_report.plots = reports_data

        if prev_nr.text != night_report.text or prev_nr.plots != night_report.plots:
            await notify_ws_clients(
                "nightreport",
                MessageType.NIGHT_REPORT,
                loc_cam,
                night_report.model_dump(),
            )
            self._night_reports[loc_cam] = night_report
        return

    async def make_per_day_data(
        self, camera: Camera, events: list[Event]
    ) -> dict[str, dict]:
        per_day_chans = camera.pd_channels()
        if not per_day_chans:
            return {}
        per_day_chan_names = [chan.name for chan in per_day_chans]
        pd_events = [e for e in events if e.channel_name in per_day_chan_names]
        if not pd_events:
            return {}
        pd_data = {e.channel_name: e.__dict__ for e in pd_events}
        return pd_data

    async def make_channel_table(
        self, camera: Camera, events: list[Event]
    ) -> dict[int, dict[str, dict]]:
        table = await make_table_from_event_list(events, camera.seq_channels())
        return table

    async def get_current_objects(
        self, location_name: str, camera: Camera
    ) -> list[dict[str, str]]:
        loc_cam = self._get_loc_cam(location_name, camera)
        return self._objects.get(loc_cam, [])

    async def get_current_events(
        self, location_name: str, camera: Camera
    ) -> list[Event]:
        loc_cam = self._get_loc_cam(location_name, camera)
        return self._events.get(loc_cam, [])

    async def get_current_channel_table(
        self, location_name: str, camera: Camera
    ) -> dict[int, dict[str, dict]]:
        loc_cam = self._get_loc_cam(location_name, camera)
        table = self._table.get(loc_cam, {})
        return table

    async def get_current_per_day_data(
        self, location_name: str, camera: Camera
    ) -> dict[str, dict[str, dict]]:
        loc_cam = self._get_loc_cam(location_name, camera)
        events = self._per_day.get(loc_cam, {})
        return {chan: event for chan, event in events.items()}

    async def get_current_metadata(self, location_name: str, camera: Camera) -> dict:
        name = camera.name
        if camera.metadata_from:
            name = camera.metadata_from
        loc_cam = f"{location_name}/{name}"
        return self._metadata.get(loc_cam, {})

    async def get_current_channel_event(
        self, location_name: str, camera_name: str, channel_name: str
    ) -> Event | None:
        loc_cam = f"{location_name}/{camera_name}/{channel_name}"
        # explicitly return None if none
        event = self._most_recent_events.get(loc_cam, None)
        return event

    async def get_current_night_report(
        self, location_name: str, camera_name: str
    ) -> NightReport:
        loc_cam = f"{location_name}/{camera_name}"
        night_report = self._night_reports.get(loc_cam, NightReport())
        return night_report

    def _get_loc_cam(self, location_name: str, camera: Camera) -> str:
        """Return `f"{location_name}/{camera.name}"`

        Parameters
        ----------
        location_name : `str`
            Name of location.
        camera : `Camera`
            A Camera object.

        Returns
        -------
        `str`
            The joining of the two strings with a backslash in-between.
        """
        loc_cam = f"{location_name}/{camera.name}"
        return loc_cam

    async def get_next_prev_event(
        self, location_name: str, event: Event
    ) -> tuple[dict | None, ...]:
        loc_cam = f"{location_name}/{event.camera_name}"
        table = self._table.get(loc_cam, {})
        nxt_prv = await get_next_previous_from_table(table, event)
        return nxt_prv

    def night_report_exists(self, location_name: str, camera_name: str) -> bool:
        loc_cam = f"{location_name}/{camera_name}"
        # returns True if there is a night report, False otherwise
        return self._night_reports.get(loc_cam, False) is not False

    async def get_latest_data(
        self,
        location: Location,
        camera: Camera,
        channel_name: str,
        service: str,
    ) -> AsyncGenerator:
        match service:
            case "camera":
                if channel_data := await self.get_current_channel_table(
                    location.name, camera
                ):
                    yield MessageType.CAMERA_TABLE, channel_data

                if metadata := await self.get_current_metadata(location.name, camera):
                    yield MessageType.CAMERA_METADATA, metadata

                if per_day := await self.get_current_per_day_data(
                    location.name, camera
                ):
                    yield MessageType.CAMERA_PER_DAY, per_day

                if self.night_report_exists(location.name, camera.name):
                    yield MessageType.CAMERA_PER_DAY, {"nightReportLink": "current"}

            case "channel":
                if event := await self.get_current_channel_event(
                    location.name, camera.name, channel_name
                ):
                    yield MessageType.CHANNEL_EVENT, event.__dict__

            case "nightreport":
                night_report = await self.get_current_night_report(
                    location.name, camera.name
                )
                # Check for equality with empty NightReport (from
                # pydantic.BaseModel)
                if night_report != NightReport():
                    yield MessageType.NIGHT_REPORT, night_report.model_dump()
