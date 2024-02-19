import asyncio
from concurrent.futures import ThreadPoolExecutor

import structlog
from lsst.ts.rubintv.background.background_helpers import get_metadata_obj
from lsst.ts.rubintv.handlers.websocket_notifiers import notify_of_update
from lsst.ts.rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReport,
    NightReportPayload,
    get_current_day_obs,
)
from lsst.ts.rubintv.models.models_helpers import (
    make_table_from_event_list,
    objects_to_events,
    objects_to_ngt_reports,
)
from lsst.ts.rubintv.s3client import S3Client
from lsst.ts.rubintv.utils import get_exception_traceback_str


class CurrentPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    _clients: dict[str, S3Client] = {}

    _objects: dict[str, list] = {}

    _events: dict[str, list[Event]] = {}
    _metadata: dict[str, dict] = {}
    _table: dict[str, dict[int, dict[str, dict]]] = {}

    _per_day: dict[str, dict[str, Event]] = {}
    _singles: dict[str, Event] = {}

    _nr_metadata: dict[str, NightReport] = {}
    _nr_reports: dict[str, set[NightReport]] = {}

    def __init__(self, locations: list[Location]) -> None:
        self.completed_first_poll = False
        self.locations = locations
        self._current_day_obs = get_current_day_obs()
        for location in locations:
            self._clients[location.name] = S3Client(
                location.profile_name, location.bucket_name
            )

    async def clear_all_data(self) -> None:
        self._objects = {}
        self._events = {}
        self._metadata = {}
        self._table = {}
        self._per_day = {}
        self._singles = {}
        self._nr_metadata = {}
        self._nr_reports = {}

    async def poll_buckets_for_todays_data(self) -> None:
        try:
            while True:
                logger = structlog.get_logger(__name__)
                if self._current_day_obs != get_current_day_obs():
                    await self.clear_all_data()
                day_obs = self._current_day_obs = get_current_day_obs()

                for location in self.locations:
                    client = self._clients[location.name]
                    for camera in location.cameras:
                        if not camera.online:
                            continue

                        prefix = f"{camera.name}/{day_obs}"

                        # handle blocking call in async code
                        executor = ThreadPoolExecutor(max_workers=3)
                        loop = asyncio.get_event_loop()
                        objects = await loop.run_in_executor(
                            executor, client.list_objects, prefix
                        )
                        loc_cam = await self._get_loc_cam(location.name, camera)
                        objects = await self.seive_out_metadata(
                            objects, prefix, location, camera
                        )
                        objects = await self.seive_out_night_reports(
                            objects, loc_cam, location
                        )
                        await self.process_channel_objects(objects, loc_cam, camera)
                self.completed_first_poll = True
                await asyncio.sleep(1)
        except Exception as e:
            logger.error("Error", error=e, traceback=get_exception_traceback_str(e))

    async def process_channel_objects(
        self, objects: list[dict[str, str]], loc_cam: str, camera: Camera
    ) -> None:
        if objects and (
            loc_cam not in self._objects or objects != self._objects[loc_cam]
        ):
            self._objects[loc_cam] = objects
            events = await objects_to_events(objects)
            self._events[loc_cam] = events
            await self.update_channel_events(events, camera, loc_cam)

            pd_data = await self.make_per_day_data(camera, events)
            self._per_day[loc_cam] = pd_data
            await notify_of_update("camera", "perDay", loc_cam, pd_data)

            table = await self.make_channel_table(camera, events)
            self._table[loc_cam] = table
            await notify_of_update("camera", "channelData", loc_cam, table)

    async def update_channel_events(
        self, events: list[Event], camera: Camera, loc_cam: str
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
                chan_lookup not in self._singles
                or self._singles[chan_lookup] != current_event
            ):
                self._singles[chan_lookup] = current_event
                await notify_of_update(
                    "channel", "event", chan_lookup, current_event.__dict__
                )

    async def seive_out_metadata(
        self,
        objects: list[dict[str, str]],
        prefix: str,
        location: Location,
        camera: Camera,
    ) -> list[dict[str, str]]:
        logger = structlog.get_logger(__name__)
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
        loc_cam = await self._get_loc_cam(location.name, camera)
        md_key = md_obj["key"]
        client = self._clients[location.name]
        data = await get_metadata_obj(md_key, client)
        if data and (loc_cam not in self._metadata or data != self._metadata[loc_cam]):
            self._metadata[loc_cam] = data
            # some channels e.g. Star Tracker and Star Tracker Wide
            # share the same metadata file. If it changes, the websocket
            # clients listening to those cameras need to be notified too.
            to_notify = [camera]
            to_notify.extend(
                c for c in location.cameras if c.metadata_from == camera.name
            )
            for cam in to_notify:
                loc_cam = await self._get_loc_cam(location.name, cam)
                await notify_of_update("camera", "metadata", loc_cam, data)

    async def seive_out_night_reports(
        self,
        objects: list[dict[str, str]],
        loc_cam: str,
        location: Location,
    ) -> list[dict[str, str]]:
        logger = structlog.get_logger(__name__)
        report_objs, objects = await self.filter_night_report_objects(objects)
        if report_objs:
            try:
                await self.process_night_report_objects(report_objs, loc_cam, location)
            except ValueError:
                logger.error("More than one night report metadata file for {loc_cam}")
        return objects

    async def filter_night_report_objects(
        self, objects: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        report_objs = [o for o in objects if "night_report" in o["key"]]
        filtered = [o for o in objects if o not in report_objs]
        return (report_objs, filtered)

    async def process_night_report_objects(
        self,
        report_objs: list[dict[str, str]],
        loc_cam: str,
        location: Location,
    ) -> None:
        message: NightReportPayload = {}
        reports = await objects_to_ngt_reports(report_objs)
        text_reports = [r for r in reports if r.group == "metadata"]
        if len(text_reports) > 1:
            raise ValueError
        if text_reports:
            text_report = text_reports[0]
            if (
                loc_cam not in self._nr_metadata
                or self._nr_metadata[loc_cam] != text_report
            ):
                key = text_report.key
                client = self._clients[location.name]
                text_obj = await get_metadata_obj(key, client)
                if text_obj:
                    message["text"] = text_obj
            self._nr_metadata[loc_cam] = text_report
            reports.remove(text_report)

        stored = set()
        if loc_cam in self._nr_reports:
            stored = self._nr_reports[loc_cam]
        to_update = list(set(reports) - stored)
        if to_update:
            message["plots"] = to_update
            self._nr_reports[loc_cam] = set(reports)
        if message:
            await notify_of_update("nightreport", "nightReport", loc_cam, message)
        return

    async def make_per_day_data(
        self, camera: Camera, events: list[Event]
    ) -> dict[str, Event]:
        per_day_chans = camera.pd_channels()
        if not per_day_chans:
            return {}
        per_day_chan_names = [chan.name for chan in per_day_chans]
        pd_events = [e for e in events if e.channel_name in per_day_chan_names]
        if not pd_events:
            return {}
        pd_data = {e.channel_name: e for e in pd_events}
        return pd_data

    async def make_channel_table(
        self, camera: Camera, events: list[Event]
    ) -> dict[int, dict[str, dict]]:
        table = await make_table_from_event_list(events, camera.seq_channels())
        return table

    async def get_current_objects(
        self, location_name: str, camera: Camera
    ) -> list[dict[str, str]]:
        loc_cam = await self._get_loc_cam(location_name, camera)
        return self._objects.get(loc_cam, [])

    async def get_current_events(
        self, location_name: str, camera: Camera
    ) -> list[Event]:
        loc_cam = await self._get_loc_cam(location_name, camera)
        return self._events.get(loc_cam, [])

    async def get_current_channel_table(
        self, location_name: str, camera: Camera
    ) -> dict[int, dict[str, dict]]:
        loc_cam = await self._get_loc_cam(location_name, camera)
        events = self._events.get(loc_cam)
        if not events:
            return {}
        return await make_table_from_event_list(events, camera.seq_channels())

    async def get_current_per_day_data(
        self, location_name: str, camera: Camera
    ) -> dict[str, dict[str, dict]]:
        loc_cam = await self._get_loc_cam(location_name, camera)
        events = self._per_day.get(loc_cam, {})
        return {chan: event.__dict__ for chan, event in events.items()}

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
        event = self._singles.get(loc_cam, None)
        return event

    async def get_current_night_report(
        self, location_name: str, camera_name: str
    ) -> NightReportPayload:
        loc_cam = f"{location_name}/{camera_name}"
        payload: NightReportPayload = {}
        if text_nr := self._nr_metadata.get(loc_cam):
            client = self._clients[location_name]
            text_dict = await get_metadata_obj(text_nr.key, client)
            payload["text"] = text_dict
        if loc_cam in self._nr_reports:
            if plots := self._nr_reports[loc_cam]:
                payload["plots"] = list(plots)
        return payload

    async def night_report_exists(self, location_name: str, camera_name: str) -> bool:
        loc_cam = f"{location_name}/{camera_name}"
        exists = loc_cam in self._nr_metadata or loc_cam in self._nr_reports
        return exists

    async def _get_loc_cam(self, location_name: str, camera: Camera) -> str:
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
