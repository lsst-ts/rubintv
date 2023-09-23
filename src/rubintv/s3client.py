import json
from typing import Any

import boto3
import structlog
from botocore.exceptions import ClientError

from rubintv.config import config


class S3Client:
    def __init__(self, profile_name: str) -> None:
        endpoint_url = config.s3_endpoint_url
        session = boto3.Session(
            region_name="us-east-1", profile_name=profile_name
        )
        if endpoint_url is not None and not endpoint_url == "testing":
            self._client = session.client("s3", endpoint_url=endpoint_url)
        else:
            self._client = session.client("s3")
        self._bucket_name = profile_name

    def list_objects(self, prefix: str) -> list[dict[str, str]]:
        objects = []
        response = self._client.list_objects_v2(
            Bucket=self._bucket_name, Prefix=prefix
        )
        while True:
            for content in response.get("Contents", []):
                object = {}
                object["key"] = content["Key"]
                object["hash"] = content["ETag"].strip('"')
                objects.append(object)
            if "NextContinuationToken" not in response:
                break
            response = self._client.list_objects_v2(
                Bucket=self._bucket_name,
                Prefix=prefix,
                ContinuationToken=response["NextContinuationToken"],
            )
        return objects

    def get_object(self, key: str) -> dict | None:
        logger = structlog.get_logger(__name__)
        try:
            obj = self._client.get_object(Bucket=self._bucket_name, Key=key)
            return json.loads(obj["Body"].read())
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info(f"Object for key: {key} not found.")
            return None

    def get_binary_object(self, key: str) -> Any | None:
        # TODO: use some kind of caching to store the last few images
        # so they don't need to be downloaded from the bucket for every client
        logger = structlog.get_logger(__name__)
        try:
            obj = self._client.get_object(Bucket=self._bucket_name, Key=key)
            data: bytes = obj["Body"].read()
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info(f"Object for key: {key} not found.")
            return None
