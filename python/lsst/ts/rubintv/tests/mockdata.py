import json
import logging
import random
from datetime import timedelta
from itertools import chain
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from lsst.ts.rubintv.models.models import Channel, Event, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import Camera, Location

today = get_current_day_obs()
the_past = today - timedelta(days=100)
_metadata = {f"col{n}": "dummy" for n in range(1, 6)}
md_json = json.dumps(_metadata)


class RubinDataMocker:
    def __init__(self, locations: list[Location], s3_required: bool = False) -> None:
        self._locations = locations
        if s3_required:
            self.create_buckets()
        self.s3_required = s3_required
        self.location_channels: dict[str, list[Channel]] = {}
        self.channel_objs: dict[str, dict[str, list[dict[str, str]]]] = {}
        self.events: dict[str, list[Event]] = {}
        self.metadata: dict[str, dict[str, dict]] = {}
        self.mock_up_data()

    def create_buckets(self) -> None:
        for location in self._locations:
            bucket_name = location.bucket_name
            # mock bucket requires a legit region name
            s3 = boto3.resource("s3", region_name="us-east-1")
            print(f"Creating bucket: {bucket_name}")
            bucket = s3.Bucket(bucket_name)
            bucket.create()

    def mock_up_data(self) -> None:
        for location in self._locations:
            loc_name = location.name
            self.events[loc_name] = []
            self.location_channels[loc_name] = []
            groups = location.camera_groups.values()
            camera_names = list(chain(*groups))
            cameras = location.cameras
            for cam_name in camera_names:
                camera: Camera | None
                if camera := find_first(cameras, "name", cam_name):
                    self.location_channels[loc_name].append(camera.channels)
                    channel_objs = self.mock_channel_objs(location, camera)
                    self.channel_objs[loc_name][cam_name] = channel_objs
                    self.events[loc_name].append(self.dicts_to_events(channel_objs))
                    self.metadata[loc_name][cam_name] = self.mock_camera_metadata(
                        location, camera
                    )

    def mock_channel_objs(
        self, location: Location, camera: Camera
    ) -> list[dict[str, str]]:
        # loc_channels: dict[str, list[Channel]] = {}
        channel_data: list[dict[str, str]] = []
        iterations = 3
        for channel in camera.channels:
            for index in range(iterations):
                seq_num = f"{index:06}"

                if channel.per_day and index == iterations - 1:
                    seq_num = random.choice((seq_num, "final"))

                key = (
                    f"{camera.name}/{today}/{channel.name}/{seq_num}/"
                    f"mocked_event.jpg"
                )

                if self.s3_required:
                    upload_file(
                        Path(__file__).parent / "assets/testcard_f.jpg",
                        location.bucket_name,
                        key,
                    )
                channel_data.append({"key": key, "hash": str(random.getrandbits(128))})
        return channel_data

    def dicts_to_events(self, channel_dicts: list[dict[str, str]]) -> list[Event]:
        events = [Event(**cd) for cd in channel_dicts]
        return events

    async def get_mocked_seq_events(self, location: Location) -> list[Event]:
        events = self.events.get(location.name)
        if events is None:
            return []
        channels = self.location_channels[location.name]
        seq_chan_names = [c for c in channels if not c.per_day]
        seq_chan_events = [e for e in events if e.channel_name in seq_chan_names]
        return seq_chan_events

    def mock_camera_metadata(
        self, location: Location, camera: Camera
    ) -> dict[str, str]:
        key = f"{camera.name}/{today}/metadata.json"
        metadata = {key: md_json}

        if self.s3_required:
            upload_fileobj(md_json, location.bucket_name, key)
        return metadata


def mock_event_movies() -> None:
    pass


def mock_night_report_metadata() -> None:
    pass


def mock_night_report_plots() -> None:
    pass


def upload_file(file_name: Path | str, bucket_name: str, key: str) -> bool:
    """Upload a file to an S3 bucket.

    Parameters
    ----------
    file_name: `Path` | `str`
      Name/path of file to upload.
    bucket: `str`
      Name of bucket to upload to.
    key: `str`
      Name for the file in the bucket.

    Returns
    -------
    uploaded: `bool`
      True if file was uploaded, else False.
    """
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, bucket_name, key)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def upload_fileobj(json_str: str, bucket_name: str, key: str) -> bool:
    """Upload a file-like object to an S3 bucket.

    Parameters
    ----------
    file_obj:
      File-like object to upload.
    bucket: `str`
      Name of bucket to upload to.
    key: `str`
      Name for the file in the bucket.

    Returns
    -------
    uploaded: `bool`
      True if object was uploaded, else False.
    """
    s3_client = boto3.client("s3")
    try:
        s3_client.put_object(Bucket=bucket_name, Body=json_str, Key=key)
    except ClientError as e:
        logging.error(e)
        return False
    return True
