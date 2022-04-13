"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page"
    "get_recent_table",
    "events",
    "current",
]

from ast import Lambda
from asyncio.log import logger
from datetime import datetime, date, timedelta
from typing import List, Optional
from unicodedata import name

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import Channel, Event, Camera
from rubintv.timer import Timer

from rubintv.app import getCurrentDayObs

cameras = {
    "auxtel": Camera(
        name="Auxtel", slug="auxtel", online = True
    ),
    "comcam": Camera(
        name="Comcam", slug="comcam", online = False
    ),
    "lsstcam": Camera(
        name="LSSTcam", slug="lsstcam", online = False
    ),
    "allsky": Camera(
        name="All Sky", slug="allsky", online = False
    )
}

per_event_channels = {
    "monitor": Channel(
        name="Monitor",
        prefix="auxtel_monitor",
        endpoint="monitorevents",
        css_class="monitor"
    ),
    "spec": Channel(
        name="Spectrum", prefix="summit_specexam", endpoint="specevents", css_class="spec"
    ),
    "im": Channel(
        name="Image Analysis", prefix="summit_imexam", endpoint="imevents", css_class="im"
    ),
    "mount": Channel(
        name="Mount",
        prefix="auxtel_mount_torques",
        endpoint="mountevents",
        css_class="mount"
    ),
}

per_night_channels = {
    "rollingbuffer": Channel(
        name="Rolling Buffer",
        prefix="rolling_buffer",
        endpoint="rollingbuffer"
    ),
    "movie": Channel(
        name="Tonight's Movie",
        prefix="movie",
        endpoint="movie"
    )
}

@routes.get("")
@routes.get("/")
async def get_page(request: web.Request) -> web.Response:
    page = get_formatted_page("home.jinja", title="Rubin TV Display", cameras=cameras)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{camera}")
async def get_recent_table(request: web.Request) -> web.Response:
    camera = cameras[request.match_info["camera"]]
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        events = get_most_recent_day_events(bucket)
        if camera.online:
            page = get_formatted_page(
                'cameras/camera.jinja', camera=camera, channels=per_event_channels,
                date=events[0].cleanDate(), events=events
            )
        else:
            page = get_formatted_page("cameras/not_online.jinja", camera=camera)
    logger.info("get_recent_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{camera}/historical")
async def get_historical_table(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        h = request.config_dict["rubintv/historical_data"]
        blobs = h.getBlobs()
        page = get_formatted_page("cameras/historical.jinja", blobs=blobs[:5])
    logger.info("get_historical_blobs", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{camera}/{channel}events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        page = get_single_event_page(
            request, per_event_channels[request.match_info["channel"]]
        )
    logger.info("events", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{camera}/{name}_current")
async def current(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = request.match_info["camera"]
        bucket = request.config_dict["rubintv/gcs_bucket"]
        channel = per_event_channels[request.match_info["name"]]
        events = get_current_event(
            channel.prefix,
            bucket,
        )
        page = get_formatted_page("current.jinja", camera=camera, event=events[0], channel=channel.name)
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_single_event_page(request: web.Request, channel: Channel) -> str:
    camera = request.match_info["camera"]
    prefix = channel.prefix
    prefix_dashes = prefix.replace("_", "-")
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    event = Event(f"https://storage.googleapis.com/{bucket.name}/{prefix}/{prefix_dashes}_dayObs_{date}_seqNum_{seq}.png")
    return get_formatted_page("single_event.jinja", camera=camera, event=event, channel=channel.name)


def get_most_recent_day_events(bucket: Bucket) -> List[Event]:
    try_date = getCurrentDayObs()
    timer = datetime.now()
    timeout = 5
    blobs = []
    while not blobs:
        try_date = try_date - timedelta(1) #no blobs? try the day defore
        prefix = get_monitor_prefix_from_date(try_date)
        blobs = list(bucket.list_blobs(prefix=prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(f"Timed out. Couldn't find most recent day's records within {timeout} seconds")
        if not blobs:
            continue
        events = {}
        events['monitor'] = get_sorted_events_from_blobs(blobs)

    for chan in per_event_channels.keys():
        if chan == 'monitor':
            continue
        prefix = per_event_channels[chan].prefix
        prefix_dashes = prefix.replace("_", "-")
        new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{try_date}_seqNum_"
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        events[chan] = get_sorted_events_from_blobs(blobs)

    match_criteron = lambda x,y: x.seq == y.seq
    return flatten_events_dict_into_list(events, match_criteron)

# passed a dict where keys are as per_night_channels keys and each corresponding value is a list of
# Image(s) from that channel, will flatten into one list of Image(s) where each channel is represented
# in the Image object's chan list
def flatten_events_dict_into_list(events: dict, match_crit: Lambda = None)->List[Event]:
    if not match_crit:
        match_crit = lambda x,y: x.seq == y.seq
    keys = list(events.keys())
    for i, event in enumerate(
        events["monitor"]
    ):  # I know there will always be a monitor style event
        events["monitor"][i].chans.append(per_event_channels["monitor"])
        for k in keys:
            if k == "monitor":
                continue
            match = False
            for mim in events[k]:
                if match_crit(event, mim):
                    events["monitor"][i].chans.append(per_event_channels[k])
                    match = True
                    events[k].remove(mim)
                    break
            if not match:
                # Ignore typing here since the template expects None if not there
                events["monitor"][i].chans.append(None)
    return events['monitor']


def get_sorted_events_from_blobs(blobs: List)->List[Event]:
    events = [
        Event(el.public_url) for el in blobs if el.public_url.endswith(".png")
    ]
    sevents = sorted(events, key=lambda x: (x.date, x.seq), reverse=True)
    return sevents


def get_formatted_page(
    template: str,
    **kwargs: dict
) -> str:
    env = Environment(
        loader=PackageLoader("rubintv"),
        autoescape=select_autoescape()
    )
    env.globals.update(zip=zip)
    templ = env.get_template(template)
    return templ.render(kwargs)

def get_current_event(
    prefix: str,
    bucket: Bucket,
) -> str:
    events = get_event_list(bucket, prefix, 1)
    if events:
        return events
    raise ValueError(f"No current event found for prefix={prefix}")


def get_event_list(bucket: Bucket, prefix: str, num: Optional[int] = None) -> List[Event]:
    blobs = bucket.list_blobs(prefix=prefix)
    sevents = get_sorted_events_from_blobs(blobs)
    if num:
        return sevents[:num]
    return sevents

def get_monitor_prefix_from_date(a_date):
  return f"auxtel_monitor/auxtel-monitor_dayObs_{a_date}"
