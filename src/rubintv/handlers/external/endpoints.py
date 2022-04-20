"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page",
    "get_recent_table",
    "events",
    "current",
]

from ast import Lambda
from asyncio.log import logger
from calendar import month_name
from datetime import datetime, date, timedelta
from typing import List, Optional
from unicodedata import name
from xmlrpc.client import Boolean

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import (
    Channel,
    Event,
    Camera,
    cameras,
    per_event_channels,
    per_night_channels,
)
from rubintv.timer import Timer

from rubintv.app import getCurrentDayObs, HistoricalData


@routes.get("")
@routes.get("/")
async def get_page(request: web.Request) -> web.Response:
    page = get_formatted_page(
        "home.jinja", title="Rubin TV Display", cameras=cameras
    )
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
                "cameras/camera.jinja",
                camera=camera,
                channels=per_event_channels,
                date=events[0].cleanDate(),
                events=events,
            )
        else:
            page = get_formatted_page(
                "cameras/not_online.jinja", camera=camera
            )
    logger.info("get_recent_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}/historical")
async def get_historical(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras[request.match_info["camera"]]
        historical = request.config_dict["rubintv/historical_data"]
        active_years = historical.get_years()
        reverse_years = sorted(active_years, reverse=True)
        year_to_display = reverse_years[0]
        years = {}
        for year in reverse_years:
            months = historical.get_months_for_year(year)
            months_days = {
                month: historical.get_days_for_month_and_year(month, year)
                for month in months
            }
            years[year] = months_days

        smrd = historical.get_second_most_recent_day()
        smrd_dict = historical.get_events_for_date(smrd)
        smrd_events = flatten_events_dict_into_list(smrd_dict)

        page = get_formatted_page(
            "cameras/historical.jinja",
            camera=camera,
            year_to_display=year_to_display,
            years=years,
            month_names=month_names(),
            date=smrd,
            events=smrd_events,
        )

    logger.info("get_historical", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}/historical/{date_str}")
async def get_historical_day_data(request: web.Request) -> web.Response:
    camera = cameras[request.match_info["camera"]]
    date_str = request.match_info["date_str"]
    historical = request.config_dict["rubintv/historical_data"]
    year, month, day = [int(s) for s in date_str.split("-")]
    the_date = date(year, month, day)
    day_dict = historical.get_events_for_date(the_date)
    day_events = flatten_events_dict_into_list(day_dict)
    page = get_formatted_page(
        "cameras/day-data-per-day-channels.jinja",
        camera=camera,
        date=the_date,
        events=day_events,
    )
    return web.Response(text=page, content_type="text/html")


def month_names():
    return [date(2000, m, 1).strftime("%B") for m in list(range(1, 13))]


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
        camera = cameras[request.match_info["camera"]]
        bucket = request.config_dict["rubintv/gcs_bucket"]
        channel = per_event_channels[request.match_info["name"]]
        event = get_current_event(
            channel.prefix,
            bucket,
        )
        page = get_formatted_page(
            "current.jinja", camera=camera, event=event, channel=channel.name
        )
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_single_event_page(request: web.Request, channel: Channel) -> str:
    camera = cameras[request.match_info["camera"]]
    prefix = channel.prefix
    prefix_dashes = prefix.replace("_", "-")
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    event = Event(
        f"https://storage.googleapis.com/{bucket.name}/{prefix}/{prefix_dashes}_dayObs_{date}_seqNum_{seq}.png"
    )
    return get_formatted_page(
        "single_event.jinja", camera=camera, event=event, channel=channel.name
    )


def get_most_recent_day_events(bucket: Bucket) -> List[Event]:
    try_date = getCurrentDayObs()
    timer = datetime.now()
    timeout = 5
    blobs = []
    while not blobs:
        try_date = try_date - timedelta(1)  # no blobs? try the day before
        prefix = get_prefix_from_date("auxtel_monitor", try_date)
        blobs = list(bucket.list_blobs(prefix=prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(
                f"Timed out. Couldn't find most recent day's records within {timeout} seconds"
            )

    events = {}
    events["monitor"] = get_sorted_events_from_blobs(blobs)

    # creates a dict where key => List of events e.g.:
    # {"monitor": [Event 1, Event 2 ...] , "im": [Event 2 ...] ... }
    for chan in per_event_channels.keys():
        if chan == "monitor":
            continue
        prefix = per_event_channels[chan].prefix
        new_prefix = get_prefix_from_date(prefix, try_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        events[chan] = get_sorted_events_from_blobs(blobs)

    return flatten_events_dict_into_list(events)


def seq_num_equal(this_event, that_event) -> Boolean:
    if not hasattr(that_event, "seq"):
        return False
    else:
        return this_event.seq == that_event.seq


def flatten_events_dict_into_list(events: dict) -> List[Event]:
    """passed a dict where keys are as per_night_channels keys and each corresponding value is a list of
    events from that channel, will flatten into one list of events where each channel is represented
    in the event object's chan list (or None if it doesn't exist for that event seq num) i.e:
    from: {"monitor": [Event 1, Event 2 ...] , "im": [Event 2 ...] ... }
    to: [Event 1 (chans=['monitor', None, None, None]), Event 2 (chans=['monitor', 'im', None, None], ... ]
    """
    # make an iterator out of each channel's list of events
    event_iters = [iter(li) for li in events.values()]
    # store the channel names in order to use in the loop
    chan_lookup = list(per_event_channels.keys())
    # make a list with the first event in each channel list
    each_event = [next(it, None) for it in event_iters]
    for event in events["monitor"]:
        monitor_event = each_event[0]
        # make a list for each channel- true if seq num matches monitor event seq num, false otherwise
        list_of_matches = [
            seq_num_equal(monitor_event, other_event)
            for other_event in each_event
        ]
        # for each of the channels, add corresponding channel object to the monitor event
        # if there was a seq num match and None if not
        event.chans = [
            (matches and per_event_channels[chan_lookup[i]]) or None
            for i, matches in enumerate(list_of_matches)
        ]
        # if there was a match, move that channel's image list iterator to the next one
        each_event = [
            (list_of_matches[i] and next(it, None)) or each_event[i]
            for i, it in enumerate(event_iters)
        ]
    return events["monitor"]


def get_sorted_events_from_blobs(blobs: List) -> List[Event]:
    events = [
        Event(el.public_url) for el in blobs if el.public_url.endswith(".png")
    ]
    sevents = sorted(events, key=lambda x: (x.date, x.seq), reverse=True)
    return sevents


def get_formatted_page(template: str, **kwargs: dict) -> str:
    env = Environment(
        loader=PackageLoader("rubintv"), autoescape=select_autoescape()
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
        try_date = try_date - timedelta(1)  # no blobs? try the day defore
        new_prefix = get_prefix_from_date(prefix, try_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(
                f"Timed out. Couldn't find most recent day's records within {timeout} seconds"
            )

    events = get_sorted_events_from_blobs(blobs)
    return events[0]


def get_prefix_from_date(prefix, a_date):
    prefix_dashes = prefix.replace("_", "-")
    new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{a_date}_seqNum_"
    return new_prefix
