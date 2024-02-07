import json
import logging
import random
from datetime import timedelta
from itertools import chain
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from lsst.ts.rubintv.models.models import Camera, Location, get_current_day_obs
from lsst.ts.rubintv.models.models_helpers import find_first

today = get_current_day_obs()
the_past = today - timedelta(days=100)
_metadata = {f"col{n}": "dummy" for n in range(1, 6)}
md_json = json.dumps(_metadata)


def mock_up_data(locations: list[Location]) -> None:
    """Given the list of locations and cameras, cycles round the channels of
    each referenced camera and uploads a testcard image with the corresponding
    key to the bucket.

    This is not safe to use if mocking is not already switched on as it might
    mutate the bucket.

    mock data for:
    Event images
    f"{camera_name}/{day_obs}/{channel_name}/{seq_num:06}/{camera_name}_{day_obs}_{seq_num:06}.png"
    Event movies
    f"{camera_name}/{day_obs}/{channel_name}/[{seq_num:06}|final]/{camera_name}_{day_obs}_[{seq_num:06}|final].mp4"
    Event metadata
    f"{camera_name}/{day_obs}/metadata.json"
    Night Report metadata
    f"{camera_name}/{day_obs}/night_report/{camera_name}_night_report_{day_obs}_md.json"
    Night Report plots

    Parameters
    ----------
    locations : `list` [`Location`]
        List of locations.
    cameras : `list` [`Camera`]
        List of cameras.
    """
    for location in locations:
        bucket_name = location.bucket_name

        # mock bucket requires a legit region name
        s3 = boto3.resource("s3", region_name="us-east-1")
        print(f"Creating bucket: {bucket_name}")
        bucket = s3.Bucket(bucket_name)
        bucket.create()

        groups = location.camera_groups.values()
        camera_names = list(chain(*groups))

        cameras = location.cameras

        for camera_name in camera_names:
            camera: Camera | None
            if camera := find_first(cameras, "name", camera_name):
                mock_channel_images(camera, bucket_name)
                mock_camera_metadata(camera, bucket_name)


def mock_channel_images(camera: Camera, bucket_name: str) -> None:
    iterations = 3
    for channel in camera.channels:
        for index in range(iterations):
            seq_num = f"{index:06}"

            if channel.per_day and index == iterations - 1:
                seq_num = random.choice((seq_num, "final"))

            # upload a file for today.
            upload_file(
                Path(__file__).parent / "assets/testcard_f.jpg",
                bucket_name,
                (
                    f"{camera.name}/{today}/{channel.name}/{seq_num}/"
                    f"mocked_event.jpg"
                ),
            )


def mock_camera_metadata(camera: Camera, bucket_name: str) -> None:
    # upload a dummy metadata file.
    upload_fileobj(
        md_json, bucket_name, f"{camera.name}/{today}/metadata.json"
    )


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
