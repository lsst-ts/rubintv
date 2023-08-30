import asyncio
import json

import boto3
import structlog
from botocore.exceptions import ClientError

from rubintv.handlers.websocket import (
    notify_camera_update,
    notify_channel_update,
)
from rubintv.models.models import Event, Location, get_current_day_obs


class BucketPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    _client = boto3.client("s3")
    _current_objects: dict[str, list | None] = {}
    _current_metadata: dict[str, dict | None] = {}
    _current_channels: dict[str, Event | None] = {}
    _current_nr_metadata: dict[str, dict] = {}
    # _current_

    def __init__(self, locations: list[Location]) -> None:
        self.locations = locations

    async def poll_buckets_for_todays_data(self) -> None:
        logger = structlog.get_logger(__name__)
        while True:
            try:
                current_day_obs = get_current_day_obs()
                for loc in self.locations:
                    for camera in loc.cameras:
                        if not camera.online:
                            continue

                        prefix = f"{camera.name}/{current_day_obs}"
                        objects = self.list_objects(loc.bucket_name, prefix)

                        camera_ref = f"{loc.name}/{camera.name}"
                        try:
                            (
                                md_obj,
                                objects,
                            ) = self.filter_camera_metadata_object(objects)
                        except ValueError:
                            logger.error(
                                f"More than one metadata file found for "
                                f"{prefix}"
                            )

                        if md_obj:
                            await self.process_metadata_file(
                                md_obj, camera_ref, loc.bucket_name
                            )

                        (
                            night_reports,
                            objects,
                        ) = self.filter_night_report_objects(objects)

                        # check for differences in the remaining objects - they
                        # should all be channel event objects by this point
                        if objects and (
                            camera_ref not in self._current_objects
                            or objects != self._current_objects[camera_ref]
                        ):
                            self._current_objects[camera_ref] = objects

                        changed_events = objects_to_events(objects)
                        for e in changed_events:
                            chan_lookup = f"{camera_ref}/{e.channel_name}"
                            if (
                                chan_lookup not in self._current_channels
                                or self._current_channels[chan_lookup] is None
                                or self._current_channels[chan_lookup] != e
                            ):
                                self._current_channels[chan_lookup] = e
                            logger.info(f"{chan_lookup}: {e}")
                            await notify_channel_update((chan_lookup, e))

                        cam_msg = (f"{loc.name}/{camera.name}", changed_events)
                        await notify_camera_update(cam_msg)

                await asyncio.sleep(3)
            except Exception as e:
                logger.error(e)

    def filter_camera_metadata_object(
        self, objects: list[dict[str, str]]
    ) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
        """Given a list of objects, seperates out the camera metadata dict
        object, if it exists, having made sure there is only one metadata file
        for that day.

        Parameters
        ----------
        objects : `list` [`dict`[`str`, `str`]]
            A list of dicts that represent s3 objects comprising `"url"` and
            `"hash"` keys.

        Returns
        -------
        `tuple` [`dict` [`str`, `str`] | `None`, `list` [`dict` [`str`,`str`]]]
            A tuple for unpacking with the dict representing the metadata json
            file, or None if there isn't one and the remaining list of objects.

        Raises
        ------
        ValueError
            If there is more than one metadata file, a ValueError is raised.
        """
        md_objs = [o for o in objects if o["url"].endswith("metadata.json")]
        if len(md_objs) > 1:
            raise ValueError()
        md_obj = None
        filtered_objs = objects
        if md_objs != []:
            md_obj = md_objs[0]
            objects.pop(objects.index(md_obj))
        return (md_obj, filtered_objs)

    async def process_metadata_file(
        self, md_obj: dict[str, str], camera_ref: str, bucket_name: str
    ) -> None:
        data = self.get_object(bucket_name, md_obj["url"])
        if (
            camera_ref not in self._current_metadata
            or data != self._current_metadata[camera_ref]
        ):
            self._current_metadata[camera_ref] = data
            md_msg = (camera_ref, data)
            await notify_camera_update(md_msg)

    def filter_night_report_objects(
        self, objects: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        reports = [o for o in objects if o["url"].find("night_report")]
        filtered = [o for o in objects if o not in reports]
        return (reports, filtered)

    async def process_night_report_objects(
        self,
        report_objs: list[dict[str, str]],
        camera_ref: str,
        bucket_name: str,
    ) -> None:
        return

    async def get_current_camera(
        self, location_name: str, camera_name: str
    ) -> list[dict[str, str]] | None:
        lookup = f"{location_name}/{camera_name}"
        if lookup in self._current_objects:
            return self._current_objects[lookup]
        else:
            return None

    def list_objects(
        self, bucket_name: str, prefix: str
    ) -> list[dict[str, str]]:
        objects = []
        response = self._client.list_objects_v2(
            Bucket=bucket_name, Prefix=prefix
        )
        while True:
            for content in response.get("Contents", []):
                object = {}
                object["url"] = content["Key"]
                object["hash"] = content["ETag"].strip('"')
                objects.append(object)
            if "NextContinuationToken" not in response:
                break
            response = self._client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                ContinuationToken=response["NextContinuationToken"],
            )
        return objects

    def get_object(self, bucket_name: str, key: str) -> dict | None:
        logger = structlog.get_logger(__name__)
        try:
            obj = self._client.get_object(Bucket=bucket_name, Key=key)
            return json.loads(obj["Body"].read())
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info(f"Object for key: {key} not found.")
            return None


def objects_to_events(objects: list[dict]) -> list[Event]:
    logger = structlog.get_logger(__name__)
    events = []
    for object in objects:
        try:
            event = Event(**object)
            events.append(event)
        except ValueError as e:
            logger.info(e)
    return events
