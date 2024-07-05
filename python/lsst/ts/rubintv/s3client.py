import json
from typing import Any

from aiobotocore.session import AioBaseClient, AioSession
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
        self._session = AioSession(profile=profile_name)
        self._bucket_name = bucket_name
        self._client = None

    async def _get_client(self) -> AioBaseClient:
        if not self._client:
            async with self._session.create_client(
                "s3", endpoint_url=self.endpoint_url, region_name="us-east-1"
            ) as client:
                self._client = client
        return self._client

    async def async_list_objects(self, prefix: str) -> list[dict[str, str]]:
        async with await self._get_client() as client:
            objects = []
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=self._bucket_name, Prefix=prefix
            ):
                for content in page.get("Contents", []):
                    obj = {"key": content["Key"], "hash": content["ETag"].strip('"')}
                    objects.append(obj)
            return objects

    async def async_get_object(self, key: str) -> dict[str, Any]:
        async with await self._get_client() as client:
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
                    logger.info(f"Object for key: {key} not found.")
                return {}

    async def get_raw_object(self, key: str) -> StreamingBody:
        async with await self._get_client() as client:
            try:
                obj = await client.get_object(Bucket=self._bucket_name, Key=key)
                data = obj["Body"]
                assert isinstance(data, StreamingBody)
                return data
            except ClientError:
                raise HTTPException(status_code=404, detail=f"No such file for: {key}")

    async def get_movie(self, key: str, headers: dict[str, str] | None = None) -> Any:
        async with await self._get_client() as client:
            try:
                data = await client.get_object(
                    Bucket=self._bucket_name, Key=key, **(headers or {})
                )
                return data
            except ClientError:
                raise HTTPException(status_code=404, detail=f"No such file for: {key}")
