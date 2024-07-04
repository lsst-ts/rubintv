import json
from typing import Any

from aiobotocore.session import AioSession
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from fastapi.exceptions import HTTPException
from lsst.ts.rubintv.config import config as app_config
from lsst.ts.rubintv.config import rubintv_logger

logger = rubintv_logger()

__all__ = ["S3Client"]


class S3Client:
    def __init__(self, profile_name: str, bucket_name: str) -> None:
        self.endpoint_url = app_config.s3_endpoint_url
        self.session = AioSession(profile=profile_name)
        self._bucket_name = bucket_name

    async def async_list_objects(self, prefix: str) -> list[dict[str, str]]:
        async with self.session.create_client(
            "s3", endpoint_url=self.endpoint_url, region_name="us-east-1"
        ) as client:
            objects = []
            response = await client.list_objects_v2(
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
                response = await client.list_objects_v2(
                    Bucket=self._bucket_name,
                    Prefix=prefix,
                    ContinuationToken=response["NextContinuationToken"],
                )
            return objects

    async def async_get_object(self, key: str) -> dict[str, Any]:
        async with self.session.create_client(
            "s3", endpoint_url=self.endpoint_url, region_name="us-east-1"
        ) as client:
            try:
                obj = await client.get_object(Bucket=self._bucket_name, Key=key)
                str_data = await obj["Body"].read()
                data = json.loads(str_data)
                assert isinstance(data, dict)
                for k in data.keys():
                    assert isinstance(k, str)
                return data
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.info("Object for key: {key} not found.", key=key)
                return {}

    async def get_raw_object(self, key: str) -> StreamingBody:
        async with self.session.create_client(
            "s3", endpoint_url=self.endpoint_url, region_name="us-east-1"
        ) as client:
            try:
                obj = await client.get_object(Bucket=self._bucket_name, Key=key)
                data = obj["Body"]
                assert isinstance(data, StreamingBody)
                return data
            except ClientError:
                raise HTTPException(status_code=404, detail=f"No such file for: {key}")

    async def get_movie(self, key: str, headers: dict[str, str] | None = None) -> Any:
        async with self.session.create_client(
            "s3", endpoint_url=self.endpoint_url, region_name="us-east-1"
        ) as client:
            try:
                data = await client.get_object(
                    Bucket=self._bucket_name, Key=key, **(headers or {})
                )
                return data
            except ClientError:
                raise HTTPException(status_code=404, detail=f"No such file for: {key}")
