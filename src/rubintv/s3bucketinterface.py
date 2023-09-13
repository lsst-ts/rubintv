import json

import boto3
import structlog
from botocore.exceptions import ClientError


class S3BucketInterface:
    def __init__(self) -> None:
        self._client = boto3.client("s3")

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
                object["key"] = content["Key"]
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
