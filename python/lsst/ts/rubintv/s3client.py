import asyncio
import json
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from fastapi.exceptions import HTTPException
from lsst.ts.rubintv.config import EARLIEST_HISTORICAL_DATE
from lsst.ts.rubintv.config import config as app_config
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import get_current_day_obs

config = BotoConfig(retries={"max_attempts": 10, "mode": "standard"})
logger = rubintv_logger()

__all__ = ["S3Client"]


class S3Client:
    def __init__(
        self, profile_name: str, bucket_name: str, endpoint_url: str | None = None
    ) -> None:
        session = boto3.Session(region_name="us-east-1", profile_name=profile_name)
        if app_config.s3_endpoint_url == "testing":
            endpoint_url = "testing"
            self._client = session.client("s3")
        else:
            if endpoint_url is None:
                # Use the default endpoint URL from the config if not provided
                # in the Location.
                endpoint_url = app_config.s3_endpoint_url
            self._client = session.client(
                "s3", endpoint_url=endpoint_url, config=config
            )
        self._bucket_name = bucket_name
        self._endpoint_url = endpoint_url

    async def async_list_objects(self, prefix: str) -> list[dict[str, str]]:
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=3)
        return await loop.run_in_executor(executor, self.list_objects, prefix)

    def list_objects(self, prefix: str) -> list[dict[str, str]]:
        objects = []
        try:
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
        except ClientError as e:
            logger.error(
                f"Error listing objects in bucket: {self._bucket_name} at "
                f"{self._endpoint_url} with prefix: {prefix}",
                error=e,
            )
        return objects

    async def async_list_objects_by_date_parallel(
        self,
        prefix: str,
        start_date: date | None = None,
        end_date: date | None = None,
        num_workers: int = 8,
    ) -> AsyncGenerator[tuple[str, list[dict[str, str]]], None]:
        """Stream S3 objects using parallelized date-based prefixes.

        Parallelizes S3 listing across multiple date-based prefixes.
        Instead of listing a single prefix sequentially, it splits the date
        range into daily prefixes and fetches them in parallel using a
        thread pool. This enables concurrent S3 API calls across different
        prefixes.

        Parameters
        ----------
        prefix : `str`
            Base prefix (e.g., "lsstcam/")
        start_date : `date` | `None`, optional
            Optional start date (inclusive). Defaults to earliest historical
            date.
        end_date : `date` | `None`, optional
            Optional end date (inclusive). Defaults to today.
        num_workers : `int`, optional
            Number of worker threads for parallel prefix listing,
            by default 8.

        Yields
        ------
        `tuple`[`str`, `list`[`dict`[`str`, `str`]]]
            Tuples of (date_prefix, objects) where date_prefix is the
            specific daily prefix (e.g., "lsstcam/2026-03-18") and objects
            are the S3 objects (one per day).
        """
        today = get_current_day_obs()
        if start_date is None:
            # Default to earliest historical date
            start_date = date.fromisoformat(EARLIEST_HISTORICAL_DATE)
        if end_date is None:
            # Default to today
            end_date = today

        # Ensure start_date <= end_date for loop logic
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        logger.info(
            f"Starting parallel prefix listing for bucket: {self._bucket_name} "
            f"at {self._endpoint_url} with base prefix: {prefix}",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            num_workers=num_workers,
        )

        # Generate daily prefixes
        date_prefixes = []
        current_date = start_date

        while current_date <= end_date:
            date_prefix = f"{prefix}{current_date.year:04d}-{current_date.month:02d}-{current_date.day:02d}"
            date_prefixes.append(date_prefix)
            current_date = current_date + timedelta(days=1)

        logger.info(
            f"Generated {len(date_prefixes)} daily prefixes for parallel listing"
        )

        # Reverse to fetch most recent months first
        date_prefixes.reverse()

        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=12)

        # Semaphore to limit concurrent S3 requests
        semaphore = asyncio.Semaphore(12)

        def list_prefix_blocking(date_prefix: str) -> tuple[str, list[dict[str, str]]]:
            """Blocking function to list a single date prefix."""
            try:
                objects = self.list_objects(date_prefix)
                return (date_prefix, objects)
            except Exception as e:
                logger.error(f"Error listing prefix {date_prefix}: {e}")
                return (date_prefix, [])

        async def fetch_prefix_with_semaphore(
            date_prefix: str,
        ) -> tuple[str, list[dict[str, str]]]:
            """Fetch a prefix with semaphore to limit concurrency."""
            async with semaphore:
                return await loop.run_in_executor(
                    executor, list_prefix_blocking, date_prefix
                )

        # Fetch all prefixes in parallel with concurrency limit
        tasks = [fetch_prefix_with_semaphore(dp) for dp in date_prefixes]

        # Yield results as they complete, not after all complete
        for completed_task in asyncio.as_completed(tasks):
            date_prefix, result = await completed_task
            if result:
                yield (date_prefix, result)

    def _get_object(self, key: str) -> dict[str, Any]:
        try:
            obj = self._client.get_object(Bucket=self._bucket_name, Key=key)
            data = json.loads(obj["Body"].read())
            assert isinstance(data, dict)
            for k in data.keys():
                assert isinstance(k, str)
            return data
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.info("Object for key not found.", key=key)
            else:
                logger.error(
                    f"Error retrieving object from S3: "
                    f"bucket={self._bucket_name}, key={key}, error={error_code}",
                    error=e,
                )
            return {}
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving object from S3: bucket={self._bucket_name}, key={key}",
                error=e,
            )
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
