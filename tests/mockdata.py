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
            self.s3_client = boto3.client("s3")
            self.create_buckets()
        self.s3_required = s3_required
        self.location_channels: dict[str, list[Channel]] = {}
        self.channel_objs: dict[str, list[dict[str, str]]] = {}
        self.empty_channel: dict[str, str | None] = {}
        self.events: dict[str, list[Event]] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.mock_up_data()

    def cleanup(self) -> None:
        print("Started cleaning...")
        self.delete_buckets()

        self._locations = []
        self.s3_required = False
        self.location_channels = {}
        self.channel_objs = {}
        self.empty_channel = {}
        self.events = {}
        self.metadata = {}
        print("Finished cleaning...")

    def delete_buckets(self) -> None:
        if self.s3_required:
            s3 = boto3.resource("s3", region_name="us-east-1")
            for location in self._locations:
                bucket_name = location.bucket_name
                bucket = s3.Bucket(bucket_name)
                print(f"Emptying bucket: {bucket_name}")
                bucket.objects.all().delete()

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
                    if not camera.online:
                        continue
                    loc_cam = f"{loc_name}/{cam_name}"
                    self.location_channels[loc_name].append(camera.channels)
                    channel_objs, empty_channel = self.mock_channel_objs(
                        location, camera
                    )
                    self.channel_objs[loc_cam] = channel_objs
                    self.empty_channel[loc_cam] = empty_channel
                    self.events[loc_cam] = self.dicts_to_events(channel_objs)
                    self.metadata[loc_cam] = self.mock_camera_metadata(location, camera)

    def mock_channel_objs(
        self, location: Location, camera: Camera
    ) -> tuple[list[dict[str, str]], None | str]:
        channel_data: list[dict[str, str]] = []
        iterations = 8

        empty_channel = None
        if camera.seq_channels():
            empty_channel = random.choice(camera.seq_channels()).name

        for channel in camera.channels:
            if empty_channel and channel.name == empty_channel:
                continue
            for index in range(iterations):
                seq_num = f"{index:06}"

                if channel.per_day and index == iterations - 1:
                    seq_num = random.choice((seq_num, "final"))

                key = (
                    f"{camera.name}/{today}/{channel.name}/{seq_num}/"
                    f"mocked_event.jpg"
                )

                hash: str | None = None
                if self.s3_required:
                    if self.upload_file(
                        Path(__file__).parent / "assets/testcard_f.jpg",
                        location.bucket_name,
                        key,
                    ):
                        hash = self.get_obj_hash(location.bucket_name, key)
                if hash is None:
                    hash = str(random.getrandbits(128))
                channel_data.append({"key": key, "hash": hash})
        return (channel_data, empty_channel)

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
            self.upload_fileobj(md_json, location.bucket_name, key)
        return metadata

    def mock_event_movies(self) -> None:
        pass

    def mock_night_report_metadata(self) -> None:
        pass

    def mock_night_report_plots(self) -> None:
        pass

    def upload_file(self, file_name: Path | str, bucket_name: str, key: str) -> bool:
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
        try:
            self.s3_client.upload_file(file_name, bucket_name, key)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def upload_fileobj(self, json_str: str, bucket_name: str, key: str) -> bool:
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
        try:
            self.s3_client.put_object(Bucket=bucket_name, Body=json_str, Key=key)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def get_obj_hash(self, bucket_name: str, key: str) -> str:
        try:
            res = self.s3_client.get_object_attributes(
                Bucket=bucket_name, Key=key, ObjectAttributes=["ETag"]
            )
        except ClientError as e:
            logging.error(e)
            return ""
        return res["ETag"]
