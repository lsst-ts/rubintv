"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page",
    "get_admin_page",
    "reload_historical",
    "request_heartbeat_for_channel",
    "request_all_heartbeats",
    "get_all_sky_current",
    "get_all_sky_current_update",
    "get_allsky_historical",
    "get_allsky_historical_movie",
    "get_recent_table",
    "update_todays_table",
    "get_historical",
    "get_historical_day_data",
    "events",
    "current",
]

import json
from datetime import date
from typing import Any, Optional

from aiohttp import web
from aiohttp_jinja2 import render_string, render_template, template
from google.api_core.exceptions import NotFound
from google.cloud.storage import Bucket

from rubintv import __version__
from rubintv.handlers import routes
from rubintv.models.historicaldata import HistoricalData
from rubintv.models.models import (
    Camera,
    Channel,
    Event,
    cameras,
    get_current_day_obs,
    production_services,
)
from rubintv.timer import Timer

HEARTBEATS_PREFIX = "heartbeats"


@routes.get("")
@routes.get("/")
@template("home.jinja")
async def get_page(request: web.Request) -> dict[str, Any]:
    title = build_title(request=request)
    return {"title": title, "cameras": cameras}


@routes.get("/admin")
@template("admin.jinja")
async def get_admin_page(request: web.Request) -> dict[str, Any]:
    title = build_title("Admin", request=request)
    return {
        "title": title,
        "services": production_services,
        "version": __version__,
    }


@routes.post("/reload_historical")
async def reload_historical(request: web.Request) -> web.Response:
    historical = request.config_dict["rubintv/historical_data"]
    historical.reload()
    return web.Response(text="OK", content_type="text/plain")


@routes.get("/admin/heartbeat/{heartbeat_prefix}")
async def request_heartbeat_for_channel(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    prefix = request.match_info["heartbeat_prefix"]
    heartbeat_prefix = "/".join([HEARTBEATS_PREFIX, prefix])
    heartbeats = get_heartbeats(bucket, heartbeat_prefix)
    if heartbeats and len(heartbeats) == 1:
        hb_json = heartbeats[0]
    else:
        hb_json = {}
    json_res = json.dumps(hb_json)
    return web.Response(text=json_res, content_type="application/json")


@routes.get("/admin/heartbeats")
async def request_all_heartbeats(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    heartbeats = get_heartbeats(bucket, HEARTBEATS_PREFIX)
    json_res = json.dumps(heartbeats)
    return web.Response(text=json_res, content_type="application/json")


def get_heartbeats(bucket: Bucket, prefix: str) -> list[dict]:
    hb_blobs = list(bucket.list_blobs(prefix=prefix))
    heartbeats = []
    for hb_blob in hb_blobs:
        try:
            the_blob = bucket.get_blob(hb_blob.name)
            blob_content = the_blob.download_as_string()
        except NotFound:
            print(f"Error: {hb_blob.name} not found.")
        if not blob_content:
            continue
        hb = json.loads(blob_content)
        hb["url"] = hb_blob.name
        heartbeats.append(hb)
    return heartbeats


@routes.get("/allsky")
@template("cameras/allsky.jinja")
async def get_all_sky_current(request: web.Request) -> dict[str, Any]:
    title = build_title("All Sky", request=request)
    historical = request.config_dict["rubintv/historical_data"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    camera = cameras["allsky"]
    image_channel = camera.channels["image"]
    current = get_current_event(camera, image_channel, bucket, historical)
    movie_channel = camera.channels["movie"]
    movie = get_current_event(camera, movie_channel, bucket, historical)
    return {
        "title": title,
        "camera": camera,
        "current": current,
        "movie": movie,
    }


@routes.get("/allsky/update/{channel}")
async def get_all_sky_current_update(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    historical = request.config_dict["rubintv/historical_data"]
    camera = cameras["allsky"]
    channel_name = request.match_info["channel"]
    channel = camera.channels[channel_name]
    current = get_current_event(camera, channel, bucket, historical)
    json_dict = {
        "channel": channel_name,
        "url": current.url,
        "date": current.clean_date(),
        "seq": current.seq,
        "name": current.name,
    }
    json_res = json.dumps(json_dict)
    return web.Response(text=json_res, content_type="application/json")


@routes.get("/allsky/historical")
@template("cameras/allsky-historical.jinja")
async def get_allsky_historical(request: web.Request) -> dict[str, Any]:
    title = build_title("All Sky", "Historical", request=request)
    historical: HistoricalData = request.config_dict["rubintv/historical_data"]
    logger = request["safir/logger"]

    with Timer() as timer:
        camera = cameras["allsky"]

        years = historical.get_camera_calendar(camera)
        most_recent_year = next(iter(years.keys()))

        channel = camera.channels["movie"]
        movie = historical.get_most_recent_event(camera, channel)

    logger.info("get_allsky_historical", duration=timer.seconds)
    return {
        "title": title,
        "camera": camera,
        "year_to_display": most_recent_year,
        "years": years,
        "month_names": month_names(),
        "movie": movie,
    }


@routes.get("/allsky/historical/{date_str}")
@template("cameras/allsky-historical.jinja")
async def get_allsky_historical_movie(request: web.Request) -> dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras["allsky"]
        historical = request.config_dict["rubintv/historical_data"]

        date_str = request.match_info["date_str"]
        title = build_title("All Sky", "Historical", date_str, request=request)

        year, month, day = [int(s) for s in date_str.split("-")]
        the_date = date(year, month, day)
        all_events = historical.get_events_for_date(camera, the_date)

        years = historical.get_camera_calendar(camera)
        movie = all_events["movie"][0]
    logger.info("get_allsky_historical_movie", duration=timer.seconds)
    return {
        "title": title,
        "camera": camera,
        "years": years,
        "year_to_display": year,
        "month_names": month_names(),
        "movie": movie,
    }


def get_image_viewer_link(day_obs: date, seq_num: int) -> str:
    url = (
        "http://ccs.lsst.org/FITSInfo/view.html?"
        f"image=AT_O_{day_obs}_{seq_num:06}"
        "&raft=R00&color=grey&bias=Simple+Overscan+Correction"
        "&scale=Per-Segment&source=RubinTV"
    )
    return url


def get_event_page_link(camera: Camera, channel: Channel, event: Event) -> str:
    return f"/rubintv/{camera.slug}/{channel.endpoint}/{event.clean_date()}/{event.seq}"


@routes.get("/{camera}")
async def get_recent_table(request: web.Request) -> web.Response:
    cam_name = request.match_info["camera"]
    try:
        camera = cameras[cam_name]
    except KeyError:
        raise web.HTTPNotFound()

    title = build_title(camera.name, request=request)
    logger = request["safir/logger"]
    with Timer() as timer:
        if not camera.online:
            context: dict[str, Any] = {"camera": camera}
            template = "cameras/not_online.jinja"
        else:
            bucket = request.config_dict["rubintv/gcs_bucket"]
            historical = request.config_dict["rubintv/historical_data"]

            the_date, events = get_most_recent_day_events(
                bucket, camera, historical
            )

            metadata_json = get_metadata_json(bucket, camera, the_date, logger)
            per_day = get_per_day_channels(bucket, camera, the_date, logger)

            template = "cameras/camera.jinja"
            context = {
                "title": title,
                "camera": camera,
                "date": the_date.strftime("%Y-%m-%d"),
                "events": events,
                "metadata": metadata_json,
                "per_day": per_day,
                "viewer_link": get_image_viewer_link,
                "event_page_link": get_event_page_link,
            }
    logger.info("get_recent_table", duration=timer.seconds)
    response = render_template(template, request, context)
    return response


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
        primary_channel = list(camera.channels)[0]
        lookup_prefix = camera.channels[primary_channel].prefix
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
        recent_events[primary_channel] = get_sorted_events_from_blobs(blobs)
        events_dict = build_dict_with_remaining_channels(
            bucket, camera, recent_events, the_date
        )

        events = make_table_rows_from_columns_by_seq(events_dict)

        metadata_json = get_metadata_json(bucket, camera, the_date, logger)
        per_day = get_per_day_channels(bucket, camera, the_date, logger)

        context = {
            "camera": camera,
            "date": the_date,
            "events": events,
            "metadata": metadata_json,
            "per_day": per_day,
            "viewer_link": get_image_viewer_link,
            "event_page_link": get_event_page_link,
        }
        table_html = render_string(
            "cameras/data-table-header.jinja", request, context
        )
        per_day_html = render_string(
            "cameras/per-day-channels.jinja", request, context
        )
        html_parts = {"table": table_html, "per_day": per_day_html}
        json_res = json.dumps(html_parts)
    logger.info("update_todays_table", duration=timer.seconds)
    return web.Response(text=json_res, content_type="application/json")


@routes.get("/{camera}/historical")
@template("cameras/historical.jinja")
async def get_historical(request: web.Request) -> dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        camera = cameras[request.match_info["camera"]]
        if not camera.has_historical:
            raise web.HTTPNotFound()
        title = build_title(camera.name, "Historical", request=request)
        historical = request.config_dict["rubintv/historical_data"]
        active_years = historical.get_years(camera)
        reverse_years = sorted(active_years, reverse=True)
        year_to_display = reverse_years[0]

        years = historical.get_camera_calendar(camera)

        smrd = historical.get_most_recent_day(camera)
        smrd_dict = historical.get_events_for_date(camera, smrd)
        smrd_events = make_table_rows_from_columns_by_seq(smrd_dict)

        metadata_json = get_metadata_json(bucket, camera, smrd, logger)
        per_day = get_per_day_channels(bucket, camera, smrd, logger)

    logger.info("get_historical", duration=timer.seconds)
    return {
        "title": title,
        "camera": camera,
        "year_to_display": year_to_display,
        "years": years,
        "month_names": month_names(),
        "date": smrd,
        "events": smrd_events,
        "metadata": metadata_json,
        "per_day": per_day,
        "viewer_link": get_image_viewer_link,
        "event_page_link": get_event_page_link,
    }


@routes.get("/{camera}/historical/{date_str}")
@template("cameras/historical.jinja")
async def get_historical_day_data(request: web.Request) -> dict[str, Any]:
    logger = request["safir/logger"]
    historical = request.config_dict["rubintv/historical_data"]
    bucket = request.config_dict["rubintv/gcs_bucket"]

    camera = cameras[request.match_info["camera"]]
    if not camera.has_historical:
        raise web.HTTPNotFound
    date_str = request.match_info["date_str"]
    title = build_title(camera.name, "Historical", date_str, request=request)

    year, month, day = [int(s) for s in date_str.split("-")]
    the_date = date(year, month, day)
    day_dict = historical.get_events_for_date(camera, the_date)
    day_events = make_table_rows_from_columns_by_seq(day_dict)

    years = historical.get_camera_calendar(camera)

    per_day = get_per_day_channels(bucket, camera, the_date, logger)
    metadata_json = get_metadata_json(bucket, camera, the_date, logger)
    return {
        "title": title,
        "camera": camera,
        "years": years,
        "month_names": month_names(),
        "date": the_date,
        "events": day_events,
        "metadata": metadata_json,
        "per_day": per_day,
        "viewer_link": get_image_viewer_link,
        "event_page_link": get_event_page_link,
    }


def get_per_day_channels(
    bucket: Bucket, camera: Camera, the_date: date, logger: Any
) -> dict[str, str]:
    """Builds a dict of per-day channels to display

    Takes a bucket, camera and a given date and returns a dict of per-day
    channels to be iterated over in the view.
    If there is nothing available for those channels, an empty dict is returned.

    Parameters
    ----------
    bucket : `Bucket`
        The app-wide Bucket instance

    camera : `Camera`
        The given Camera object

    the_date : `date`
        The datetime.date object for the given day

    logger : `Any`
        The app-wide logging object

    Returns
    -------
    per_day_channels : `dict[str, str]`
        The list of events, per channel

    """
    per_day_channels = {}
    for channel in camera.per_day_channels.keys():
        if resource_url := get_channel_resource_url(
            bucket, camera.per_day_channels[channel], the_date, logger
        ):
            per_day_channels[channel] = resource_url
    return per_day_channels


def get_channel_resource_url(
    bucket: Bucket, channel: Channel, a_date: date, logger: Any
) -> str:
    date_str = a_date.strftime("%Y%m%d")
    prefix = f"{channel.prefix}/dayObs_{date_str}"
    url = ""
    if blobs := list(bucket.list_blobs(prefix=prefix)):
        url = blobs[0].public_url
    return url


def get_metadata_json(
    bucket: Bucket, camera: Camera, a_date: date, logger: Any
) -> dict:
    date_str = a_date.strftime("%Y%m%d")
    blob_name = f"{camera.slug}_metadata/dayObs_{date_str}.json"
    metadata_json = "{}"
    if blob := bucket.get_blob(blob_name):
        metadata_json = blob.download_as_string()
    return json.loads(metadata_json)


def month_names() -> list[str]:
    return [date(2000, m, 1).strftime("%B") for m in list(range(1, 13))]


@routes.get("/{camera}/{channel}events/{date}/{seq}")
@template("single_event.jinja")
async def events(request: web.Request) -> dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        camera = cameras[request.match_info["camera"]]
        channel_name = request.match_info["channel"]
        the_date = request.match_info["date"]
        seq = request.match_info["seq"]
        channel = camera.channels[channel_name]
        title = build_title(
            camera.name, channel.name, the_date, seq, request=request
        )
        prefix = channel.prefix
        prefix_dashes = prefix.replace("_", "-")
        blob_name = (
            f"{prefix}/{prefix_dashes}_dayObs_{the_date}_seqNum_{seq}.png"
        )
        event = None
        if blob := bucket.get_blob(blob_name):
            event = Event(blob.public_url)
    logger.info("events", duration=timer.seconds)
    return {
        "title": title,
        "camera": camera,
        "channel": channel.name,
        "event": event,
        "date": the_date,
        "seq": seq,
    }


@routes.get("/{camera}/{channel}_current")
@template("current.jinja")
async def current(request: web.Request) -> dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        camera = cameras[request.match_info["camera"]]
        bucket = request.config_dict["rubintv/gcs_bucket"]
        historical = request.config_dict["rubintv/historical_data"]
        channel = camera.channels[request.match_info["channel"]]
        event = get_current_event(camera, channel, bucket, historical)
        the_date = event.clean_date()
        seq = event.seq
        title = build_title(
            camera.name, f"Current {channel.name}", request=request
        )
    logger.info("current", duration=timer.seconds)
    return {
        "title": title,
        "camera": camera,
        "event": event,
        "channel": channel.name,
        "date": the_date,
        "seq": seq,
    }


def get_most_recent_day_events(
    bucket: Bucket, camera: Camera, historical: HistoricalData
) -> tuple[date, dict[int, dict[str, Event]]]:
    primary_channel = list(camera.channels)[0]
    prefix = camera.channels[primary_channel].prefix
    events = {}
    primary_events = get_todays_events_for_prefix(prefix, bucket)
    if primary_events:
        events[primary_channel] = primary_events
        the_date = primary_events[0].obs_date
        events_dict = build_dict_with_remaining_channels(
            bucket, camera, events, the_date
        )
    else:
        the_date = historical.get_most_recent_day(camera)
        events_dict = historical.get_events_for_date(camera, the_date)
    todays_events = make_table_rows_from_columns_by_seq(events_dict)
    return (the_date, todays_events)


def build_dict_with_remaining_channels(
    bucket: Bucket,
    camera: Camera,
    events_dict: dict[str, list[Event]],
    the_date: date,
) -> dict[str, list[Event]]:
    # creates a dict where key => list of events e.g.:
    # {"monitor": [Event 1, Event 2 ...] , "im": [Event 2 ...] ... }
    primary_channel = list(camera.channels)[0]
    for chan in camera.channels:
        if chan == primary_channel:
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


def make_table_rows_from_columns_by_seq(
    events_dict: dict,
) -> dict[int, dict[str, Event]]:
    d: dict[int, dict[str, Event]] = {}
    # d == {seq: {chan1: event, chan2: event, ... }}
    for chan in events_dict:
        chan_events = events_dict[chan]
        for e in chan_events:
            if e.seq in d:
                d[e.seq].update({chan: e})
            else:
                d.update({e.seq: {chan: e}})
    return d


def get_sorted_events_from_blobs(blobs: list) -> list[Event]:
    events = [
        Event(el.public_url)
        for el in blobs
        if el.public_url.endswith(".png")
        or el.public_url.endswith(".jpg")
        or el.public_url.endswith(".mp4")
    ]
    sevents = sorted(events, key=lambda x: (x.obs_date, x.seq), reverse=True)
    return sevents


def get_todays_events_for_prefix(
    prefix: str,
    bucket: Bucket,
) -> list[Event]:
    today = get_current_day_obs()
    new_prefix = get_prefix_from_date(prefix, today)
    events = []
    blobs = list(bucket.list_blobs(prefix=new_prefix))
    if blobs:
        events = get_sorted_events_from_blobs(blobs)
    return events


def get_all_events_for_prefix(
    prefix: str,
    bucket: Bucket,
) -> list[Event]:
    blobs = list(bucket.list_blobs(prefix=prefix))
    return blobs


def get_current_event(
    camera: Camera,
    channel: Channel,
    bucket: Bucket,
    historical: HistoricalData,
) -> Event:
    events = get_todays_events_for_prefix(channel.prefix, bucket)
    if events:
        latest = events[0]
    else:
        latest = historical.get_most_recent_event(camera, channel)
    return latest


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
