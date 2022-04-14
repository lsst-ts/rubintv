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
        blobs = h.get_blobs()
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
        event = get_current_event(
            channel.prefix,
            bucket,
        )
        page = get_formatted_page("current.jinja", camera=camera, event=event, channel=channel.name)
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
        prefix = get_prefix_from_date('auxtel_monitor', try_date)
        blobs = list(bucket.list_blobs(prefix=prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(f"Timed out. Couldn't find most recent day's records within {timeout} seconds")

    events = {}
    events['monitor'] = get_sorted_events_from_blobs(blobs)

    for chan in per_event_channels.keys():
        if chan == 'monitor':
            continue
        prefix = per_event_channels[chan].prefix
        new_prefix = get_prefix_from_date(prefix, try_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        events[chan] = get_sorted_events_from_blobs(blobs)

    match_criteron = lambda x,y: x.seq == y.seq
    return flatten_events_dict_into_list(events, match_criteron)

"""passed a dict where keys are as per_night_channels keys and each corresponding value is a list of
events from that channel, will flatten into one list of events where each channel is represented
in the event object's chan list (or None if it doesn't exist for that event seq num)
"""
def flatten_events_dict_into_list(events:dict, match_crit: Lambda = None) -> List[Event]:
    if not match_crit:
        match_crit = lambda x,y: x.seq == y.seq
    event_iters = [iter(li) for li in events.values()]
    chan_lookup = list(per_event_channels.keys())
    each_event = [next(it, None) for it in event_iters]
    for event in events['monitor']:
        monitor_event = each_event[0]
        equal = [match_crit(monitor_event, other_event) for other_event in each_event]
        event.chans = [(equality and per_event_channels[chan_lookup[i]]) or None for i, equality in enumerate(equal)]
        each_event = [(equal[i] and next(it, None)) or each_event[i] for i, it in enumerate(event_iters)]
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
) -> Event:
    try_date = getCurrentDayObs()
    timer = datetime.now()
    timeout = 10
    blobs = []
    while not blobs:
        try_date = try_date - timedelta(1) #no blobs? try the day defore
        new_prefix = get_prefix_from_date(prefix, try_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(f"Timed out. Couldn't find most recent day's records within {timeout} seconds")

    events = get_sorted_events_from_blobs(blobs)
    return events[0]


def get_prefix_from_date(prefix, a_date):
    prefix_dashes = prefix.replace("_", "-")
    new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{a_date}_seqNum_"
    return new_prefix
