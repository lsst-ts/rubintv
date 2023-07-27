import logging
from datetime import timedelta
from itertools import chain
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from rubintv.models.helpers import find_first
from rubintv.models.models import Camera, Location, get_current_day_obs


def mock_up_data(locations: list[Location], cameras: list[Camera]) -> None:
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

        for camera_name in camera_names:
            if camera := find_first(cameras, "name", camera_name):
                if camera.channels:
                    for index, channel in enumerate(camera.channels):
                        # upload a file for today
                        upload_file(
                            Path(__file__).parent
                            / "static/images/testcard_f.jpg",
                            bucket_name,
                            (
                                f"{camera_name}/{today}/{channel.name}/"
                                f"{index:06}.jpg"
                            ),
                        )
                        # upload one for 100 days ago
                        upload_file(
                            Path(__file__).parent
                            / "static/images/testcard_f.jpg",
                            bucket_name,
                            (
                                f"{camera_name}/{the_past}/{channel.name}/"
                                f"{index:06}.jpg"
                            ),
                        )


def upload_file(
    file_name: Path | str, bucket_name: str, object_name: str
) -> bool:
    """Upload a file to an S3 bucket.

    Parameters
    ----------
    file_name: `Path` | `str`
      Name/path of file to upload.
    bucket: `str`
      Name of bucket to upload to.

    Returns
    -------
    uploaded: `bool`
      True if file was uploaded, else False.
    """
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, bucket_name, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True
