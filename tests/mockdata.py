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
        include_metadata: bool = False,
        metadata_entries_per_camera: int = 100,
    ) -> None:
        """
        Initialize the RubinDataMocker instance.

        Parameters
        ----------
        locations : `list` [`Location`]
            A list of Location objects representing various observation
            locations.
        day_obs : `date`, optional
            The observation day, defaults to today.
        s3_required : `bool`, optional
            Set to True if S3 operations are required, otherwise defaults
            to False.
        populate: `bool`, optional
            Set to False if an empty mocker is required. Defaults to True.
        include_metadata : `bool`, optional
            Whether to create metadata files for cameras. Defaults to False.
        metadata_entries_per_camera : `int`, optional
            Number of metadata entries per camera. Defaults to 100.
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
        self.include_metadata = include_metadata
        self.metadata_entries_per_camera = metadata_entries_per_camera
        self.metadata: dict[str, dict] = {}
        self.metadata_files: list[str] = []
        if populate:
            self.mock_up_data()

    def create_buckets(self) -> None:
        for location in self._locations:
            bucket_name = location.bucket_name
            # TODO: Remove the below line once the issue is fixed in boto3
            # See DM-49439 for more details
            # Below function call raises "DeprecationWarning:
            # datetime.datetime.utcnow() is deprecated"
            # This is a known issue and will be fixed in the next release
            # of boto3.
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

                    self.location_channels[loc_name].extend(camera.channels)
                    self.add_seq_objs(location, camera)

        # Create metadata files if enabled
        if self.include_metadata:
            self._create_metadata_files()

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
        key = (
            f"{camera_name}/{day_obs}/{channel_name}/{seq_num}/"
            f"{camera_name}_{channel_name}_{day_obs}_{seq_num}.jpg"
        )
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
        location : `Location`
            The location for which to retrieve the sequence events.
        camera : `Camera`
            The camera for which to retrieve the sequence events.
        channel : `Channel`
            The channel for which to retrieve the sequence events.

        Returns
        -------
        `list` [`Event`]
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

    def _create_metadata_files(self) -> None:
        """Create metadata files for testing purposes.

        This method creates metadata entries for each camera at each location,
        storing them in both in-memory structures and optionally S3 if
        required.
        """
        from lsst.ts.rubintv.config import rubintv_logger

        logger = rubintv_logger()

        logger.info("Creating metadata files for testing")

        for location in self._locations:
            loc_name = location.name
            for camera in location.cameras:
                if not camera.online:
                    continue

                camera_name = camera.name

                # Create metadata entries for this camera
                for i in range(self.metadata_entries_per_camera):
                    metadata_key = f"{loc_name}-{camera_name}-metadata-{i:03d}"
                    metadata_content = {
                        "seq_num": str(i),
                        "date_obs": f"{self.day_obs}",
                        "camera": camera_name,
                        "location": loc_name,
                        "image_type": "OBJECT",
                        "exposure_time": 30.0,
                        "filter": "r",
                        "target": f"target_{i}",
                        "airmass": 1.2,
                        "azimuth": float(i % 360),
                        "altitude": 45.0,
                        "test_data": True,
                    }

                    self.metadata[metadata_key] = metadata_content
                    self.metadata_files.append(metadata_key)

                # Create S3 metadata file once per camera if S3 is required
                if self.s3_required:
                    self._create_s3_metadata(location, camera)

        logger.info(f"Created {len(self.metadata_files)} metadata files for testing")

    def _create_s3_metadata(
        self,
        location: Location,
        camera: Camera,
    ) -> None:
        """Create metadata files in S3 for a camera.

        Parameters
        ----------
        location : `Location`
            The location where the camera is located
        camera : `Camera`
            The camera to create metadata for
        """
        bucket_name = location.bucket_name
        # Use the expected metadata.json pattern that CurrentPoller recognizes
        metadata_key = f"{camera.name}/{self.day_obs}/metadata.json"

        # Create a dictionary with all sequence entries for this camera
        if not hasattr(self, "_s3_metadata_created"):
            self._s3_metadata_created: set[str] = set()

        # Only create one metadata.json file per camera per day
        camera_day_key = f"{camera.name}-{self.day_obs}"
        if camera_day_key not in self._s3_metadata_created:
            # Create metadata with all sequence entries for this camera
            full_metadata = {}
            for i in range(self.metadata_entries_per_camera):
                full_metadata[str(i)] = {
                    "camera": camera.name,
                    "day_obs": str(self.day_obs),
                    "seq_num": i,
                    "timestamp": f"{self.day_obs}",
                    "image_type": "OBJECT",
                    "exposure_time": 30.0,
                    "filter": "r",
                    "target": f"target_{i}",
                    "airmass": 1.2,
                    "azimuth": float(i % 360),
                    "altitude": 45.0,
                    "test_data": True,
                }

            try:
                json_str = json.dumps(full_metadata)
                self.s3_client.put_object(
                    Bucket=bucket_name, Body=json_str, Key=metadata_key
                )
                self._s3_metadata_created.add(camera_day_key)
            except ClientError as e:
                logging.error(f"Failed to upload metadata to S3: {e}")

    def get_metadata_files(self) -> list[str]:
        """Get the list of created metadata file keys.

        Returns
        -------
        metadata_files : `list` [`str`]
            List of metadata file keys that were created
        """
        return self.metadata_files.copy()

    def get_metadata(self, key: str) -> dict | None:
        """Get metadata content by key.

        Parameters
        ----------
        key : `str`
            The metadata key to retrieve

        Returns
        -------
        metadata : `dict` | `None`
            The metadata content, or None if not found
        """
        return self.metadata.get(key)
