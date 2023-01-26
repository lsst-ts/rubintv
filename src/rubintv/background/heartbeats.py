import asyncio
import json
import time
from typing import Any, Dict, List

from aiohttp import web
from google.api_core.exceptions import NotFound
from google.cloud.storage.client import Bucket

__all__ = ["poll_for_heartbeats", "process_heartbeats", "get_heartbeats"]

HEARTBEATS_PREFIX = "heartbeats"


async def poll_for_heartbeats(app: web.Application) -> None:
    try:
        while True:
            for location in app["rubintv/models"].locations:
                # just use summit bucket to start
                bucket = app[f"rubintv/buckets/{location}"]
                heartbeats_json_arr = get_heartbeats(bucket, HEARTBEATS_PREFIX)
                heartbeats = process_heartbeats(heartbeats_json_arr)
                app["rubintv/heartbeats"][location] = heartbeats
            await asyncio.sleep(30)
    except asyncio.exceptions.CancelledError:
        print("Polling for heartbeats cancelled")


def get_heartbeats(bucket: Bucket, prefix: str) -> List[Dict]:
    hb_blobs = list(bucket.list_blobs(prefix=prefix))
    heartbeats = []
    for hb_blob in hb_blobs:
        blob_content = None
        try:
            the_blob = bucket.blob(hb_blob.name)
            blob_content = the_blob.download_as_bytes()
        except NotFound:
            print(f"Error: {hb_blob.name} not found.")
        if not blob_content:
            continue
        else:
            hb = json.loads(blob_content)
            hb["url"] = hb_blob.name
            heartbeats.append(hb)
    return heartbeats


def process_heartbeats(
    heartbeats_json_list: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    heartbeats = {}
    t = time.time()
    for hb in heartbeats_json_list:
        channel = hb["channel"]
        next = hb["nextExpected"]
        curr = hb["currTime"]
        active = next > t
        heartbeats[channel] = {"active": active, "next": next, "curr": curr}
    return heartbeats
