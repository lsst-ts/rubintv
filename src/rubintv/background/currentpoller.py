import asyncio
from concurrent.futures import ThreadPoolExecutor

import structlog

from rubintv.handlers.websocket_helpers import (
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
    NightReportMessage,
    get_current_day_obs,
)
from rubintv.s3client import S3Client


class CurrentPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    _clients: dict[str, S3Client] = {}

    _objects: dict[str, list | None] = {}
    _metadata: dict[str, dict | None] = {}
    _channels: dict[str, Event | None] = {}
    _nr_metadata: dict[str, NightReport] = {}
    _nr_reports: dict[str, set[NightReport]] = {}

    def __init__(self, locations: list[Location]) -> None:
        self.locations = locations
        for location in locations:
            self._clients[location.name] = S3Client(
                profile_name=location.bucket_name
            )
            for camera in location.cameras:
                for channel in camera.channels:
                    self._channels[
                        f"{location.name}/{camera.name}/{channel.name}"
                    ] = None

    async def poll_buckets_for_todays_data(self) -> None:
        while True:
            current_day_obs = get_current_day_obs()
            for location in self.locations:
                client = self._clients[location.name]
                for camera in location.cameras:
                    if not camera.online:
                        continue
                    prefix = f"{camera.name}/{current_day_obs}"
                    # handle blocking call in async code
                    executor = ThreadPoolExecutor(max_workers=3)
                    loop = asyncio.get_event_loop()
                    objects = await loop.run_in_executor(
                        executor, client.list_objects, prefix
                    )
                    loc_cam = f"{location.name}/{camera.name}"

                    objects = await self.seive_out_metadata(
                        objects, prefix, loc_cam, location
                    )
                    objects = await self.seive_out_night_reports(
                        objects, loc_cam, location
                    )
                    await self.process_channel_objects(
                        objects, loc_cam, camera
                    )
            await asyncio.sleep(3)

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
            if self._channels[chan_lookup] != current_event:
                self._channels[chan_lookup] = current_event
                await notify_channel_update((chan_lookup, current_event))

    async def seive_out_metadata(
        self,
        objects: list[dict[str, str]],
        prefix: str,
        loc_cam: str,
        location: Location,
    ) -> list[dict[str, str]]:
        logger = structlog.get_logger(__name__)
        try:
            md_obj, objects = self.filter_camera_metadata_object(objects)
        except ValueError:
            logger.error(f"More than one metadata file found for {prefix}")

        if md_obj:
            await self.process_metadata_file(md_obj, loc_cam, location)
        return objects

    def filter_camera_metadata_object(
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
            raise ValueError()
        md_obj = None
        if md_objs != []:
            md_obj = md_objs[0]
            objects.pop(objects.index(md_obj))
        return (md_obj, objects)

    async def process_metadata_file(
        self, md_obj: dict[str, str], loc_cam: str, location: Location
    ) -> None:
        key = md_obj["key"]
        data = await self.get_metadata_obj(key, location)
        if data and (
            loc_cam not in self._metadata or data != self._metadata[loc_cam]
        ):
            self._metadata[loc_cam] = data
            md_msg = (loc_cam, data)
            await notify_camera_metadata_update(md_msg)

    async def seive_out_night_reports(
        self,
        objects: list[dict[str, str]],
        loc_cam: str,
        location: Location,
    ) -> list[dict[str, str]]:
        report_objs, objects = await self.filter_night_report_objects(objects)
        if report_objs:
            await self.process_night_report_objects(
                report_objs, loc_cam, location
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
        message: NightReportMessage = {}
        reports = await objects_to_ngt_reports(report_objs)
        text_reports = [r for r in reports if r.group == "metadata"]
        if len(text_reports) > 1:
            raise ValueError
        if text_reports:
            text_report = text_reports[0]
            if (
                not (loc_cam in self._nr_metadata)
                or self._nr_metadata[loc_cam] != text_report
            ):
                key = text_report.key
                text_obj = await self.get_metadata_obj(key, location)
                if text_obj:
                    message["text"] = text_obj
            self._nr_metadata[loc_cam] = text_report
            reports.remove(text_report)

        stored = self._nr_reports[loc_cam]
        to_update = list(set(reports) - stored)
        if to_update:
            message["plots"] = to_update
            self._nr_reports[loc_cam] = set(reports)

        if message:
            await notify_night_report_update((loc_cam, message))
        return

    async def get_metadata_obj(
        self, key: str, location: Location
    ) -> dict | None:
        client = self._clients[location.name]
        executor = ThreadPoolExecutor(max_workers=3)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(executor, client.get_object, key)
        return data

    async def get_current_objects(
        self, location_name: str, camera_name: str
    ) -> list[dict[str, str]] | None:
        loc_cam = f"{location_name}/{camera_name}"
        if loc_cam in self._objects:
            return self._objects[loc_cam]
        else:
            return None

    async def get_current_metadata(
        self, location_name: str, camera_name: str
    ) -> dict | None:
        loc_cam = f"{location_name}/{camera_name}"
        if loc_cam in self._metadata:
            return self._metadata[loc_cam]
        else:
            return None

    async def get_current_channel_event(
        self, location_name: str, camera_name: str, channel_name: str
    ) -> Event | None:
        loc_cam = f"{location_name}/{camera_name}/{channel_name}"
        event = self._channels[loc_cam]
        if event:
            event.url = await self._clients[location_name].get_presigned_url(
                event.key
            )
        return event
