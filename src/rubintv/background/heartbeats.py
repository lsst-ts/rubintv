import asyncio
import json
import time
from typing import Any, Dict, List

from aiohttp import web
from google.api_core.exceptions import NotFound
from google.cloud.storage.client import Bucket

__all__ = [
    "poll_for_heartbeats",
    "process_heartbeats",
    "download_heartbeat_objects",
]

HEARTBEATS_PREFIX = "heartbeats"


async def poll_for_heartbeats(app: web.Application) -> None:
    """Asynchronous loop that polls the buckets for heartbeat files.

    Called from within a set-up/tear-down function during the app's
    initialisation.

    Parameters
    ----------
    app : `web.Application`
        The web app.
    """
    try:
        while True:
            for location in app["rubintv/models"].locations:
                # just use summit bucket to start
                bucket = app[f"rubintv/buckets/{location}"]
                heartbeats_json_arr = download_heartbeat_objects(
                    bucket, HEARTBEATS_PREFIX
                )
                heartbeats = process_heartbeats(heartbeats_json_arr)
                app["rubintv/heartbeats"][location] = heartbeats
            await asyncio.sleep(30)
    except asyncio.exceptions.CancelledError:
        print("Polling for heartbeats cancelled")


def download_heartbeat_objects(bucket: Bucket, prefix: str) -> List[Dict]:
    """Attempts to download heartbeat objects.

    Parameters
    ----------
    bucket : `Bucket`
        The given bucket
    prefix : `str`
        The prefix for a particular heartbeat file.

    Returns
    -------
    raw_heartbeats : `List` [`Dict`]
        A list of heartbeat dicts.

    See Also
    --------
    `process_heartbeats()` for details
    """
    hb_blobs = list(bucket.list_blobs(prefix=prefix))
    heartbeat_objs = []
    for hb_blob in hb_blobs:
        try:
            the_blob = bucket.blob(hb_blob.name)
            blob_content = the_blob.download_as_bytes()
        except NotFound:
            blob_content = None
            print(f"Error: {hb_blob.name} not found.")
        if not blob_content:
            continue
        else:
            hb = json.loads(blob_content)
            hb["url"] = hb_blob.name
            heartbeat_objs.append(hb)
    return heartbeat_objs


def process_heartbeats(
    heartbeat_objs: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Takes a list of heartbeat dicts and returns a dict of simplified
    dicts keyed by channel/service name that include a boolean for the
    current status of the heartbeat.

    Parameters
    ----------
    heartbeats_json_list : `List` [`Dict` [`str`, `Any`]]
        A list of heartbeat dicts as they are as json files in the bucket

    Returns
    -------
    heartbeats : `Dict` [`str`, `Dict` [`str`, `Any`]]
        A dictionary of simplified heartbeat dicts keyed by channel/service name

    Examples
    --------
    input:
    ``
    {
        'channel': 'allsky',
        'currTime': 1675779822,
        'nextExpected': 1675780422,
        'errors': {},
        'url': 'heartbeats/allsky.json'
    }
    ``
    outputs:
    ``
    {
        'allsky': {
            'active': True,
            'next': 1675780422,
            'curr': 1675779822
        }
    }
    ``
    """
    heartbeats = {}
    t = time.time()
    for hb in heartbeat_objs:
        channel = hb["channel"]
        next = hb["nextExpected"]
        curr = hb["currTime"]
        active = next > t
        heartbeats[channel] = {"active": active, "next": next, "curr": curr}
    return heartbeats
