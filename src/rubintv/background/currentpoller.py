import asyncio
from concurrent.futures import ThreadPoolExecutor

import structlog

from rubintv.background.background_helpers import get_metadata_obj
from rubintv.handlers.websocket_notifiers import (
    notify_camera_events_update,
    notify_camera_metadata_update,
    notify_channel_update,
    notify_night_report_update,
)
from rubintv.models.helpers import objects_to_events, objects_to_ngt_reports
from rubintv.models.models import (
    Camera,
    Event,
    Location,
    NightReport,
    NightReportPayload,
    get_current_day_obs,
)
from rubintv.s3client import S3Client


class CurrentPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    _clients: dict[str, S3Client] = {}

    _objects: dict[str, list] = {}
    _metadata: dict[str, dict] = {}
    _channels: dict[str, Event] = {}
    _nr_metadata: dict[str, NightReport] = {}
    _nr_reports: dict[str, set[NightReport]] = {}

    def __init__(self, locations: list[Location]) -> None:
        self.completed_first_poll = False
        self.locations = locations
        self._current_day_obs = get_current_day_obs()
        for location in locations:
            self._clients[location.name] = S3Client(
                profile_name=location.bucket_name
            )

    async def clear_all_data(self) -> None:
        self._objects = {}
        self._metadata = {}
        self._nr_metadata = {}
        self._nr_reports = {}
        self._channels = {}

    async def poll_buckets_for_todays_data(self) -> None:
        try:
            while True:
                if self._current_day_obs != get_current_day_obs():
                    await self.clear_all_data()
                day_obs = self._current_day_obs = get_current_day_obs()
                logger = structlog.get_logger(__name__)

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
                        loc_cam = await self.build_loc_cam(location, camera)

                        objects = await self.seive_out_metadata(
                            objects, prefix, location, camera
                        )
                        objects = await self.seive_out_night_reports(
                            objects, loc_cam, location
                        )
                        await self.process_channel_objects(
                            objects, loc_cam, camera
                        )
                self.completed_first_poll = True
                await asyncio.sleep(3)
        except Exception as e:
            logger.error("Error", error=e)

    async def build_loc_cam(self, location: Location, camera: Camera) -> str:
        return f"{location.name}/{camera.name}"

    async def process_channel_objects(
        self, objects: list[dict[str, str]], loc_cam: str, camera: Camera
    ) -> None:
        if objects and (
            loc_cam not in self._objects or objects != self._objects[loc_cam]
        ):
            self._objects[loc_cam] = objects
            events = objects_to_events(objects)
            await self.update_channel_events(events, camera, loc_cam)
            cam_msg = (loc_cam, events)
            await notify_camera_events_update(cam_msg)

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
                chan_lookup not in self._channels
                or self._channels[chan_lookup] != current_event
            ):
                self._channels[chan_lookup] = current_event
                message = (chan_lookup, current_event)
                await notify_channel_update(message)

    async def seive_out_metadata(
        self,
        objects: list[dict[str, str]],
        prefix: str,
        location: Location,
        camera: Camera,
    ) -> list[dict[str, str]]:
        logger = structlog.get_logger(__name__)
        # if the metadata for this camera is under another camera's name, this
        # is a no op.
        if camera.metadata_from:
            return objects
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
        if md_objs != []:
            md_obj = md_objs[0]
            objects.pop(objects.index(md_obj))
        return (md_obj, objects)

    async def process_metadata_file(
        self, md_obj: dict[str, str], location: Location, camera: Camera
    ) -> None:
        loc_cam = await self.build_loc_cam(location, camera)
        key = md_obj["key"]
        client = self._clients[location.name]
        data = await get_metadata_obj(key, client)
        if data and (
            loc_cam not in self._metadata or data != self._metadata[loc_cam]
        ):
            self._metadata[loc_cam] = data
            to_notify = [camera]
            to_notify.extend(
                c for c in location.cameras if c.metadata_from == camera.name
            )
            for cam in to_notify:
                loc_cam = await self.build_loc_cam(location, cam)
                await notify_camera_metadata_update((loc_cam, data))

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
                await self.process_night_report_objects(
                    report_objs, loc_cam, location
                )
            except ValueError:
                logger.error(
                    "More than one night report metadata file for {loc_cam}"
                )
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
            await notify_night_report_update((loc_cam, message))
        return

    async def get_current_objects(
        self, location_name: str, camera_name: str
    ) -> list[dict[str, str]] | None:
        loc_cam = f"{location_name}/{camera_name}"
        if loc_cam in self._objects:
            return self._objects[loc_cam]
        else:
            return None

    async def get_current_metadata(
        self, location_name: str, camera: Camera
    ) -> dict | None:
        name = camera.name
        if camera.metadata_from:
            name = camera.metadata_from
        loc_cam = f"{location_name}/{name}"
        if loc_cam in self._metadata:
            return self._metadata[loc_cam]
        else:
            return None

    async def get_current_channel_event(
        self, location_name: str, camera_name: str, channel_name: str
    ) -> Event | None:
        loc_cam = f"{location_name}/{camera_name}/{channel_name}"
        if loc_cam not in self._channels:
            return None
        event = self._channels[loc_cam]
        if event:
            event.url = await self._clients[location_name].get_presigned_url(
                event.key
            )
        return event

    async def get_current_night_report(
        self, location_name: str, camera_name: str
    ) -> NightReportPayload:
        loc_cam = f"{location_name}/{camera_name}"
        payload: NightReportPayload = {}
        if loc_cam in self._nr_metadata:
            if text_nr := self._nr_metadata[loc_cam]:
                client = self._clients[location_name]
                text_dict = await get_metadata_obj(text_nr.key, client)
                payload["text"] = text_dict
        if loc_cam in self._nr_reports:
            if plots := self._nr_reports[loc_cam]:
                payload["plots"] = list(plots)
        return payload

    async def current_night_report_exists(
        self, location_name: str, camera_name: str
    ) -> bool:
        loc_cam = f"{location_name}/{camera_name}"
        exists = loc_cam in self._nr_metadata or loc_cam in self._nr_reports
        return exists
