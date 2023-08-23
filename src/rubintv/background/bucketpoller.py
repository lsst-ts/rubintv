import asyncio
import json

import boto3
import structlog
from botocore.exceptions import ClientError

from rubintv.handlers.websocket import notify_camera_clients
from rubintv.models.models import Event, Location, get_current_day_obs


class BucketPoller:
    """Polls and holds state of the current day obs data in the s3 bucket and
    notifies the websocket server of changes.
    """

    _client = boto3.client("s3")
    _current_channels: dict[str, dict[str, list | None]] = {}
    _current_metadata: dict[str, dict[str, dict | None]] = {}

    def __init__(self, locations: list[Location]) -> None:
        self.locations = locations
        # storage dict values are None by default to become lists once polled
        self._current_channels = {
            loc.name: {cam.name: None for cam in loc.cameras if cam.online}
            for loc in locations
        }
        self._current_metadata = {
            loc.name: {cam.name: None for cam in loc.cameras if cam.online}
            for loc in locations
        }

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
                        # there can only be one metadata json file per cam per
                        # day in the bucket so we can grab the first one.
                        try:
                            md_obj = next(
                                iter(
                                    [
                                        o
                                        for o in objects
                                        if o["url"].endswith("metadata.json")
                                    ]
                                )
                            )
                            objects.pop(objects.index(md_obj))
                            md = self.get_object(
                                loc.bucket_name, md_obj["url"]
                            )
                            if (
                                md
                                != self._current_metadata[loc.name][
                                    camera.name
                                ]
                            ):
                                self._current_metadata[loc.name][
                                    camera.name
                                ] = md
                                md_msg = {f"{loc.name}/{camera.name}": md}
                                await notify_camera_clients(md_msg)
                        except StopIteration:
                            logger.debug(f"No metadata found for {prefix}")

                        if (
                            objects
                            != self._current_channels[loc.name][camera.name]
                        ):
                            self._current_channels[loc.name][
                                camera.name
                            ] = objects
                        msg = {
                            f"{loc.name}/{camera.name}": objects_to_events(
                                objects
                            )
                        }
                        await notify_camera_clients(msg)

            except Exception as e:
                logger.info(e)

            await asyncio.sleep(3)

    async def get_current_state(
        self, location_name: str, camera_name: str
    ) -> list[dict[str, str]] | None:
        return self._current_channels[location_name][camera_name]

    def list_objects(self, bucket_name: str, prefix: str) -> list[dict]:
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


def objects_to_events(objects: list[dict] | None) -> list[Event] | None:
    logger = structlog.get_logger(__name__)
    if objects is None:
        return None
    events = []
    for object in objects:
        try:
            event = Event(**object)
            events.append(event)
        except ValueError as e:
            logger.info(e)
    return events
