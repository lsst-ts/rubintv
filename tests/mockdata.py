import json
import logging
import random
from datetime import date, timedelta
from itertools import chain
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from lsst.ts.rubintv.models.models import Channel, Event, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first
from lsst.ts.rubintv.models.models_init import Camera, Location

today = get_current_day_obs()
the_past = today - timedelta(days=100)


class RubinDataMocker:
    FIRST_SEQ = 0

    def __init__(
        self,
        locations: list[Location],
        day_obs: date = today,
        s3_required: bool = False,
        populate: bool = True,
    ) -> None:
        """
        Initialize the RubinDataMocker instance.

        Parameters
        ----------
        locations : `list[`Location`]`
            A list of Location objects representing various observation
            locations.
        day_obs : `date`, `optional`
            The observation day, defaults to today.
        s3_required : `bool`, `optional`
            Set to True if S3 operations are required, otherwise defaults
            to False.
        populate: `bool`, `optional`
            Set to False if an empty mocker is requires. Defaults to True.
        """
        self.last_seq: dict[str, int] = {}
        self._locations = locations
        if s3_required:
            self.s3_client = boto3.client("s3", region_name="us-east-1")
            self.create_buckets()
        self.s3_required = s3_required
        self.day_obs = day_obs
        self.location_channels: dict[str, list[Channel]] = {}
        self.empty_channel: dict[str, str] = {}
        self.events: dict[str, list[Event]] = {}
        self.seq_objs: dict[str, list[dict[str, str]]] = {}
        if populate:
            self.mock_up_data()

    def create_buckets(self) -> None:
        for location in self._locations:
            bucket_name = location.bucket_name
            self.s3_client.create_bucket(Bucket=bucket_name)

    def mock_up_data(self) -> None:
        """
        Populate mock data for cameras and channels based on the current day's
        observation.

        Returns
        -------
        None
        """
        for location in self._locations:
            loc_name = location.name
            self.location_channels[loc_name] = []
            groups = location.camera_groups.values()
            camera_names = list(chain(*groups))
            cameras = location.cameras
            for cam_name in camera_names:
                camera: None | Camera
                if camera := find_first(cameras, "name", cam_name):
                    if not camera.online:
                        continue

                    self.location_channels[loc_name].append(camera.channels)
                    self.add_seq_objs(location, camera)

    def add_seq_objs(
        self, location: Location, camera: Camera, include_empty_channel: bool = True
    ) -> None:
        loc_cam = f"{location.name}/{camera.name}"

        empty_channel = ""
        if include_empty_channel:
            seq_chans = [chan.name for chan in camera.seq_channels()]
            if seq_chans and len(seq_chans) > 1:
                empty_channel = random.choice(seq_chans)

        for channel in camera.channels:
            if empty_channel == channel.name:
                self.empty_channel[loc_cam] = empty_channel
                continue
            self.add_seq_objs_for_channel(location, camera, channel, 2)

    def add_seq_objs_for_channel(
        self, location: Location, camera: Camera, channel: Channel, num_objs: int
    ) -> None:
        channel_data: list[dict[str, str]] = []
        loc_cam = f"{location.name}/{camera.name}"
        loc_cam_chan = f"{location.name}/{camera.name}/{channel.name}"
        start = self.last_seq.get(loc_cam_chan, self.FIRST_SEQ)

        for index in range(start, start + num_objs):
            seq_num = f"{index:06}"

            if channel.per_day and index == start + num_objs - 1:
                seq_num = random.choice((seq_num, "final"))

            event_obj = self.generate_event(
                location.bucket_name, camera.name, channel.name, seq_num
            )

            channel_data.append(event_obj)
        self.last_seq[loc_cam_chan] = index

        # store the objects for testing against
        event = self.dicts_to_events(channel_data)
        if loc_cam in self.events:
            self.events[loc_cam].extend(event)
            self.seq_objs[loc_cam].extend(channel_data)
        else:
            self.events[loc_cam] = event
            self.seq_objs[loc_cam] = channel_data

    def generate_event(
        self, bucket_name: str, camera_name: str, channel_name: str, seq_num: str
    ) -> dict[str, str]:
        day_obs = self.day_obs
        key = f"{camera_name}/{day_obs}/{channel_name}/{seq_num}/mocked_event.jpg"
        hash: None | str = None
        if self.s3_required:
            if self.upload_file(
                Path(__file__).parent / "assets/testcard_f.jpg",
                bucket_name,
                key,
            ):
                hash = self.get_obj_hash(bucket_name, key)
        if hash is None:
            hash = str(random.getrandbits(128))
        return {"key": key, "hash": hash}

    def delete_channel_events(
        self, location: Location, camera: Camera, channel: Channel
    ) -> None:
        bucket_name = location.bucket_name
        loc_cam = f"{location.name}/{camera.name}"
        loc_cam_chan = f"{loc_cam}/{channel.name}"
        events = self.events.get(loc_cam, [])
        chan_evs = [ev for ev in events if ev.channel_name == channel.name]

        for ev in chan_evs:
            self.events[loc_cam].remove(ev)
            if self.s3_required:
                self.s3_client.delete_object(Bucket=bucket_name, Key=ev.key)

        if loc_cam_chan in self.last_seq:
            del self.last_seq[loc_cam_chan]
        if self.empty_channel.get(loc_cam) == channel.name:
            del self.empty_channel[loc_cam]
        if channel in self.location_channels.get(location.name, []):
            self.location_channels[location.name].remove(channel)

    def dicts_to_events(self, channel_dicts: list[dict[str, str]]) -> list[Event]:
        events = [Event(**cd) for cd in channel_dicts]
        return events

    def get_mocked_events(
        self, location: Location, camera: Camera, channel: Channel
    ) -> list[Event]:
        """
        Retrieve events for a given location.

        Parameters
        ----------
        location : Location
            The location for which to retrieve the sequence events.

        Returns
        -------
        list[Event]
            A list of Event objects representing sequence events.
        """
        loc_cam = f"{location.name}/{camera.name}"
        return [
            e for e in self.events.get(loc_cam, []) if e.channel_name == channel.name
        ]

    def mock_night_report_plot(
        self, location: Location, camera: Camera
    ) -> dict[str, str]:
        """Generate a mock night report for a camera.

        Parameters
        ----------
        location : `Location`
            The location of the camera.
        camera : `Camera`
            The given camera.

        Returns
        -------
        night_report_object: `dict`[`str`, `str`]
            A simple dict that a `NightReport` instance can be made using.
        """
        key = f"{camera.name}/{today}/night_report/Test/filename.test"
        content = "".join([chr(random.randint(32, 126)) for _ in range(20)])
        hash: None | str = None
        if self.s3_required:
            bucket = location.bucket_name
            if self.upload_fileobj(content, bucket, key):
                hash = self.get_obj_hash(bucket, key)
        if hash is None:
            hash = str(random.getrandbits(128))
        return {"key": key, "hash": hash}

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

    def upload_fileobj(self, obj: Any, bucket_name: str, key: str) -> bool:
        """Upload a file-like object to an S3 bucket.

        Parameters
        ----------
        obj: `Any`
            An object to upload.
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
            json_str = json.dumps(obj)
            self.s3_client.put_object(Bucket=bucket_name, Body=json_str, Key=key)
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def get_obj_hash(self, bucket_name: str, key: str) -> str:
        """Retrieve the hash (ETag) of an object stored in an S3 bucket.

        Parameters
        ----------
        bucket_name : `str`
            Name of the S3 bucket.
        key : `str`
            S3 key of the object.

        Returns
        -------
        etag: `str`
            The hash (ETag) of the object if retrievable, empty string
            otherwise.
        """
        try:
            res = self.s3_client.get_object_attributes(
                Bucket=bucket_name, Key=key, ObjectAttributes=["ETag"]
            )
        except ClientError as e:
            logging.error(e)
            return ""
        return res["ETag"]
