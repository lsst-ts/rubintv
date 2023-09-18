import json
import logging
from datetime import timedelta
from itertools import chain
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Location, get_current_day_obs


def mock_up_data(locations: list[Location]) -> None:
    """Given the list of locations and cameras, cycles round the channels of
    each referenced camera and uploads a testcard image with the corresponding
    key to the bucket.

    This is not safe to use if mocking is not already switched on as it might
    mutate the bucket.

    Parameters
    ----------
    locations : `list` [`Location`]
        List of locations.
    cameras : `list` [`Camera`]
        List of cameras.
    """

    today = get_current_day_obs()
    the_past = today - timedelta(days=-100)

    for location in locations:
        bucket_name = location.bucket_name

        # mock bucket requires a legit region name
        s3 = boto3.resource("s3", region_name="us-east-1")
        bucket = s3.Bucket(bucket_name)
        bucket.create()

        groups = location.camera_groups.values()
        camera_names = list(chain(*groups))

        metadata = {f"col{n}": "dummy" for n in range(1, 6)}
        md_json = json.dumps(metadata)

        cameras = location.cameras

        for camera_name in camera_names:
            camera: Camera | None
            if camera := find_first(cameras, "name", camera_name):
                if not camera.channels:
                    continue
                for index, channel in enumerate(camera.channels):
                    print(f"Uploading for {camera_name}/{channel.name}")
                    # upload a file for today.
                    upload_file(
                        Path(__file__).parent / "static/images/testcard_f.jpg",
                        bucket_name,
                        (
                            f"{camera_name}/{today}/{channel.name}/{index:06}/"
                            f"mocked_event.jpg"
                        ),
                    )
                    # upload one for 100 days ago.
                    upload_file(
                        Path(__file__).parent / "static/images/testcard_f.jpg",
                        bucket_name,
                        (
                            f"{camera_name}/{the_past}/{channel.name}/"
                            f"{index:06}/mocked_past_event.jpg"
                        ),
                    )
            # upload a dummy metadata file.
            upload_fileobj(
                md_json, bucket_name, f"{camera_name}/{today}/metadata.json"
            )


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
