"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page",
    "get_recent_table",
    "events",
    "current",
]

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.app import get_current_day_obs
from rubintv.handlers import routes
from rubintv.models import Camera, Channel, Event, cameras
from rubintv.timer import Timer


@routes.get("")
@routes.get("/")
async def get_page(request: web.Request) -> web.Response:
    title = build_title(request=request)
    page = get_formatted_page("home.jinja", title=title, cameras=cameras)
    return web.Response(text=page, content_type="text/html")


@routes.get("/allsky")
async def get_all_sky_current(request: web.Request) -> web.Response:
    title = build_title("All Sky", request=request)
    bucket = request.config_dict["rubintv/gcs_bucket"]
    camera = cameras["allsky"]
    prefix = camera.channels["image"].prefix
    current = get_current_event(prefix, bucket)
    prefix = camera.channels["monitor"].prefix
    movie = get_current_event(prefix, bucket)
    page = get_formatted_page(
        "cameras/allsky.jinja",
        title=title,
        camera=camera,
        current=current,
        movie=movie,
    )
    return web.Response(text=page, content_type="text/html")


@routes.get("/allsky/update/{channel}")
async def get_all_sky_current_update(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    camera = cameras["allsky"]
    channel_name = request.match_info["channel"]
    prefix = camera.channels[channel_name].prefix
    current = get_current_event(prefix, bucket)
    json_dict = {
        "channel": channel_name,
        "url": current.url,
        "date": current.cleanDate(),
        "seq": current.seq,
        "name": current.name,
    }
    json_res = json.dumps(json_dict)
    return web.Response(text=json_res, content_type="application/json")


@routes.get("/allsky/historical")
async def get_allsky_historical(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras["allsky"]
        historical = request.config_dict["rubintv/historical_data"]
        active_years = historical.get_years(camera)
        reverse_years = sorted(active_years, reverse=True)
        year_to_display = reverse_years[0]
        years = {}
        for year in reverse_years:
            months = historical.get_months_for_year(camera, year)
            months_days = {
                month: historical.get_days_for_month_and_year(
                    camera, month, year
                )
                for month in months
            }
            years[year] = months_days
        movie = historical.get_most_recent_event(camera)
        page = get_formatted_page(
            "cameras/allsky-historical.jinja",
            camera=camera,
            year_to_display=year_to_display,
            years=years,
            month_names=month_names(),
            movie=movie,
        )
    logger.info("get_allsky_historical", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/allsky/historical/{date_str}")
async def get_allsky_historical_movie(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras["allsky"]
        date_str = request.match_info["date_str"]
        historical = request.config_dict["rubintv/historical_data"]
        year, month, day = [int(s) for s in date_str.split("-")]
        the_date = date(year, month, day)
        all_events = historical.get_events_for_date(camera, the_date)
        movie = all_events["monitor"][0]
        page = get_formatted_page(
            "cameras/allsky-monitor.jinja", camera=camera, movie=movie
        )
    logger.info("get_allsky_historical_movie", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}")
async def get_recent_table(request: web.Request) -> web.Response:
    cam_name = request.match_info["camera"]
    try:
        camera = cameras[cam_name]
    except KeyError:
        raise web.HTTPNotFound()
    logger = request["safir/logger"]
    with Timer() as timer:
        if not camera.online:
            page = get_formatted_page(
                "cameras/not_online.jinja", camera=camera
            )
        else:
            bucket = request.config_dict["rubintv/gcs_bucket"]
            events = get_most_recent_day_events(bucket, camera)
            channels = camera.channels
            grid_columns = build_grid_columns_css(channels)
            page = get_formatted_page(
                "cameras/camera.jinja",
                camera=camera,
                channels=channels,
                date=events[0].cleanDate(),
                events=events,
                grid_columns=grid_columns,
            )
    logger.info("get_recent_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def build_grid_columns_css(channels: Dict[str, Channel]) -> str:
    grid_columns = "1fr"
    for channel in channels:
        grid_columns += " 40px"
    return grid_columns


@routes.get("/{camera}/update/{date}")
async def update_todays_table(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras[request.match_info["camera"]]
        bucket = request.config_dict["rubintv/gcs_bucket"]
        date_str = request.match_info["date"]
        year, month, day = [int(s) for s in date_str.split("-")]
        the_date = date(year, month, day)
        blobs = []
        # if the actual date is greater than displayed on the page
        # get the data from today if there is any
        current_day = get_current_day_obs()
        lookup_prefix = camera.channels["monitor"].prefix
        if the_date < current_day:
            prefix = get_prefix_from_date(lookup_prefix, current_day)
            blobs = list(bucket.list_blobs(prefix=prefix))
        # if there's no data from a more recent day then return the refreshed
        # table from today
        if not blobs:
            prefix = get_prefix_from_date(lookup_prefix, the_date)
            blobs = list(bucket.list_blobs(prefix=prefix))
        # if there was data from more recent than displayed, store the date
        # so it can be displayed instead
        else:
            the_date = current_day

        recent_events = {}
        recent_events["monitor"] = get_sorted_events_from_blobs(blobs)
        events_dict = build_dict_with_remaining_channels(
            bucket, camera, recent_events, the_date
        )
        events = flatten_events_dict_into_list(camera, events_dict)
        grid_columns = build_grid_columns_css(camera.channels)
        page = get_formatted_page(
            "cameras/data-table-header.jinja",
            camera=camera,
            date=the_date,
            events=events,
            grid_columns=grid_columns,
        )

    logger.info("update_todays_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}/historical")
async def get_historical(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras[request.match_info["camera"]]
        if not camera.has_historical:
            raise web.HTTPNotFound()
        historical = request.config_dict["rubintv/historical_data"]
        active_years = historical.get_years(camera)
        reverse_years = sorted(active_years, reverse=True)
        year_to_display = reverse_years[0]
        years = {}
        for year in reverse_years:
            months = historical.get_months_for_year(camera, year)
            months_days = {
                month: historical.get_days_for_month_and_year(
                    camera, month, year
                )
                for month in months
            }
            years[year] = months_days

        smrd = historical.get_second_most_recent_day(camera)
        smrd_dict = historical.get_events_for_date(camera, smrd)
        smrd_events = flatten_events_dict_into_list(camera, smrd_dict)

        grid_columns = build_grid_columns_css(camera.channels)

        page = get_formatted_page(
            "cameras/historical.jinja",
            camera=camera,
            year_to_display=year_to_display,
            years=years,
            month_names=month_names(),
            date=smrd,
            events=smrd_events,
            grid_columns=grid_columns,
        )

    logger.info("get_historical", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}/historical/{date_str}")
async def get_historical_day_data(request: web.Request) -> web.Response:
    camera = cameras[request.match_info["camera"]]
    if not camera.has_historical:
        return web.Response(
            status=404, reason=f"{camera.name} has no historical data"
        )
    date_str = request.match_info["date_str"]
    historical = request.config_dict["rubintv/historical_data"]
    year, month, day = [int(s) for s in date_str.split("-")]
    the_date = date(year, month, day)
    day_dict = historical.get_events_for_date(camera, the_date)
    day_events = flatten_events_dict_into_list(camera, day_dict)
    grid_columns = build_grid_columns_css(camera.channels)
    page = get_formatted_page(
        "cameras/data-table-header-with-day-channels.jinja",
        camera=camera,
        date=the_date,
        events=day_events,
        grid_columns=grid_columns,
    )
    return web.Response(text=page, content_type="text/html")


def month_names() -> List[str]:
    return [date(2000, m, 1).strftime("%B") for m in list(range(1, 13))]


@routes.get("/{camera}/{channel}events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        camera = cameras[request.match_info["camera"]]
        channel_name = request.match_info["channel"]
        date = request.match_info["date"]
        seq = request.match_info["seq"]
        page = get_single_event_page(bucket, camera, channel_name, date, seq)
    logger.info("events", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{camera}/{channel}_current")
async def current(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras[request.match_info["camera"]]
        bucket = request.config_dict["rubintv/gcs_bucket"]
        channel = camera.channels[request.match_info["channel"]]
        event = get_current_event(
            channel.prefix,
            bucket,
        )
        page = get_formatted_page(
            "current.jinja", camera=camera, event=event, channel=channel.name
        )
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_single_event_page(
    bucket: Bucket, camera: Camera, channel_name: str, date: str, seq: str
) -> str:
    channel = camera.channels[channel_name]
    prefix = channel.prefix
    prefix_dashes = prefix.replace("_", "-")
    event = Event(
        f"https://storage.googleapis.com/{bucket.name}/{prefix}/"
        f"{prefix_dashes}_dayObs_{date}_seqNum_{seq}.png"
    )
    return get_formatted_page(
        "single_event.jinja", camera=camera, event=event, channel=channel.name
    )


def get_most_recent_day_events(bucket: Bucket, camera: Camera) -> List[Event]:
    prefix = camera.channels["monitor"].prefix
    events = {}
    events["monitor"] = get_most_recent_events_for_prefix(prefix, bucket)
    the_date = events["monitor"][0].date.date()
    events_dict = build_dict_with_remaining_channels(
        bucket, camera, events, the_date
    )

    todays_events = flatten_events_dict_into_list(camera, events_dict)
    return todays_events


def build_dict_with_remaining_channels(
    bucket: Bucket,
    camera: Camera,
    events_dict: Dict[str, List[Event]],
    the_date: date,
) -> Dict[str, List[Event]]:
    # creates a dict where key => List of events e.g.:
    # {"monitor": [Event 1, Event 2 ...] , "im": [Event 2 ...] ... }
    for chan in camera.channels.keys():
        if chan == "monitor":
            continue
        prefix = camera.channels[chan].prefix
        new_prefix = get_prefix_from_date(prefix, the_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        events_dict[chan] = get_sorted_events_from_blobs(blobs)
    return events_dict


def seq_num_equal(
    this_event: Optional[Event], that_event: Optional[Event]
) -> bool:
    if this_event is None or that_event is None:
        return False
    return this_event.seq == that_event.seq


def flatten_events_dict_into_list(camera: Camera, events: dict) -> List[Event]:
    """Transforms the per_day_channels into lists per channel.

    Takes a dict where the keys are as per_day_channels keys and each
    corresponding value is a list of events from that channel. Flattens into
    one list of events where each channel is represented in the event object's
    channel list (or None if it doesn't exist for that event seq num) i.e:
    from: {"monitor": [Event 1, Event 2 ...] , "im": [Event 2 ...] ... }
    to: [Event 1 (chans=['monitor', None, None, None]),
         Event 2 (chans=['monitor', 'im', None, None], ... ]

    Parameters
    ----------
    events : `dict`
        The dict of events. See above for details.

    Returns
    -------
    event_list : `list`
        The list of events, per channel

    """
    nonevent = Event(
        """https://storage.googleapis.com/rubintv_data/
    auxtel_monitor/auxtel-monitor_dayObs_2022-02-15_seqNum_0.png"""
    )
    # make an iterator out of each channel's list of events
    chan_iters: List[Iterator] = [iter(li) for li in events.values()]
    # store the channel names in order to use in the loop
    chan_lookup = list(camera.channels.keys())
    # make a list with the first event in each channel list
    each_chan: List[Any] = [next(it, nonevent) for it in chan_iters]

    seq_list = [ev.seq for ev in each_chan]
    highest_seq_index = seq_list.index(max(seq_list))
    key_chan = chan_lookup[highest_seq_index]

    for event in events[key_chan]:
        seq_list = [ev.seq for ev in each_chan]
        highest_seq_index = seq_list.index(max(seq_list))

        monitor_event = each_chan[highest_seq_index]
        # make a list for each channel- true if seq num matches monitor
        # event seq num, false otherwise
        list_of_matches = [
            seq_num_equal(monitor_event, other_event)
            for other_event in each_chan
        ]
        # for each of the channels, add corresponding channel object to
        # the monitor event
        # if there was a seq num match and None if not
        event.chans = [
            (matches and camera.channels[chan_lookup[i]]) or None
            for i, matches in enumerate(list_of_matches)
        ]
        # if there was a match, move that channel's image list iterator to the
        # next one
        for i, it in enumerate(chan_iters):
            if list_of_matches[i]:
                each_chan[i] = next(it, nonevent)
    return events[key_chan]


def get_sorted_events_from_blobs(blobs: List) -> List[Event]:
    events = [
        Event(el.public_url)
        for el in blobs
        if el.public_url.endswith(".png")
        or el.public_url.endswith(".jpg")
        or el.public_url.endswith(".mp4")
    ]
    sevents = sorted(events, key=lambda x: (x.date, x.seq), reverse=True)
    return sevents


def get_formatted_page(template: str, **kwargs: Any) -> str:
    env = Environment(
        loader=PackageLoader("rubintv"), autoescape=select_autoescape()
    )
    env.globals.update(zip=zip)
    templ = env.get_template(template)
    return templ.render(kwargs)


def get_most_recent_events_for_prefix(
    prefix: str,
    bucket: Bucket,
) -> List[Event]:
    try_date = get_current_day_obs()
    timer = datetime.now()
    timeout = 3
    blobs: List[Any] = []
    try_date += timedelta(1)  # add a day as to not start with yesterday
    while not blobs:
        try_date = try_date - timedelta(1)  # no blobs? try the day defore
        new_prefix = get_prefix_from_date(prefix, try_date)
        blobs = list(bucket.list_blobs(prefix=new_prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            print(
                f"Looking back for blobs timed out within {timeout} seconds...\n"
                + f"Retrieving whole list for {prefix}"
            )
            blobs = get_all_events_for_prefix(prefix, bucket)
            if not blobs:
                raise TimeoutError(f"Timed out. No data found for {prefix}")
    events = get_sorted_events_from_blobs(blobs)
    return events


def get_all_events_for_prefix(
    prefix: str,
    bucket: Bucket,
) -> List[Event]:
    blobs = list(bucket.list_blobs(prefix=prefix))
    return blobs


def get_current_event(
    prefix: str,
    bucket: Bucket,
) -> Event:
    events = get_most_recent_events_for_prefix(prefix, bucket)
    return events[0]


def get_prefix_from_date(prefix: str, a_date: date) -> str:
    prefix_dashes = prefix.replace("_", "-")
    new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{a_date}_seqNum_"
    return new_prefix


def build_title(*title_parts: str, request: web.Request) -> str:
    title = request.config_dict["rubintv/site_title"]
    to_append = " - ".join(title_parts)
    if to_append:
        title += " - " + to_append
    return title
