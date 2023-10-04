import asyncio
from concurrent.futures import ThreadPoolExecutor

from rubintv.s3client import S3Client


async def get_metadata_obj(key: str, s3_client: S3Client) -> dict:
    executor = ThreadPoolExecutor(max_workers=3)
    loop = asyncio.get_event_loop()
    if data := await loop.run_in_executor(executor, s3_client.get_object, key):
        return data
    else:
        return {}
