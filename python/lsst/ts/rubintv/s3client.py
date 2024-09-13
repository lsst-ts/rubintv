import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from fastapi.exceptions import HTTPException
from lsst.ts.rubintv.config import config as app_config
from lsst.ts.rubintv.config import rubintv_logger

config = BotoConfig(retries={"max_attempts": 10, "mode": "standard"})
logger = rubintv_logger()

__all__ = ["S3Client"]


class S3Client:
    def __init__(self, profile_name: str, bucket_name: str) -> None:
        endpoint_url = app_config.s3_endpoint_url
        session = boto3.Session(region_name="us-east-1", profile_name=profile_name)
        if endpoint_url is not None and not endpoint_url == "testing":
            self._client = session.client(
                "s3", endpoint_url=endpoint_url, config=config
            )
        else:
            self._client = session.client("s3")
        self._bucket_name = bucket_name

    async def async_list_objects(self, prefix: str) -> list[dict[str, str]]:
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=3)
        return await loop.run_in_executor(executor, self.list_objects, prefix)

    def list_objects(self, prefix: str) -> list[dict[str, str]]:
        objects = []
        response = self._client.list_objects_v2(Bucket=self._bucket_name, Prefix=prefix)
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

    def _get_object(self, key: str) -> dict[str, Any]:
        try:
            obj = self._client.get_object(Bucket=self._bucket_name, Key=key)
            data = json.loads(obj["Body"].read())
            assert isinstance(data, dict)
            for k in data.keys():
                assert isinstance(k, str)
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info("Object for key: {key} not found.", key=key)
            return {}

    async def async_get_object(self, key: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=3)
        return await loop.run_in_executor(executor, self._get_object, key)

    def get_raw_object(self, key: str) -> StreamingBody:
        try:
            obj = self._client.get_object(Bucket=self._bucket_name, Key=key)
            data = obj["Body"]
            assert isinstance(data, StreamingBody)
            return data
        except ClientError:
            raise HTTPException(status_code=404, detail=f"No such file for: {key}")

    def get_movie(self, key: str, headers: dict[str, str] | None = None) -> Any:
        try:
            data = self._client.get_object(
                Bucket=self._bucket_name, Key=key, **(headers or {})
            )
            return data
        except ClientError:
            raise HTTPException(status_code=404, detail=f"No such file for: {key}")
