"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page",
    "get_admin_page",
    "heartbeats_websocket",
    "reload_historical",
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

import asyncio
import json
from datetime import date
from typing import Any, Dict, List

from aiohttp import web
from aiohttp_jinja2 import render_string, render_template, template

from rubintv.handlers import routes
from rubintv.handlers.external.endpoints_helpers import (
    build_title,
    calendar_factory,
    date_from_url_part,
    download_sort_night_report_events,
    find_location,
    get_current_event,
    get_event_page_link,
    get_image_viewer_link,
    get_metadata_json,
    get_most_recent_day_events,
    get_night_report_events,
    get_nights_report_link_type,
    get_per_day_channels,
    make_table_rows_from_columns_by_seq,
    month_names,
)
from rubintv.models.historicaldata import HistoricalData
from rubintv.models.models import (
    Event,
    Night_Report_Event,
    get_current_day_obs,
)
from rubintv.timer import Timer


@routes.get("")
@routes.get("/", name="home")
@template("home.jinja")
async def get_page(request: web.Request) -> Dict[str, Any]:
    title = build_title(request=request)
    locations = request.config_dict["rubintv/models"].locations
    return {
        "title": title,
        "locations": locations,
    }


@routes.get("/health")
async def get_health(request: web.Request) -> web.Response:
    return web.Response(text="OK", content_type="text/plain")


@routes.get("/{location}", name="location")
@template("location_home.jinja")
async def get_location_home(request: web.Request) -> Dict[str, Any]:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)
    cameras = request.config_dict["rubintv/models"].cameras
    title = build_title(location.name, request=request)
    return {"title": title, "location": location, "cameras": cameras}


@routes.get("/{location}/heartbeats_ws")
async def heartbeats_websocket(request: web.Request) -> web.WebSocketResponse:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)
    heartbeats = request.config_dict["rubintv/heartbeats"][location.slug]

    ws = web.WebSocketResponse()
    request.config_dict["websockets"].add(ws)
    try:
        await ws.prepare(request)
    except ConnectionResetError as ce:
        logger = request["safir/logger"]
        logger.error("Websocket connection error", error=ce)
    try:
        await ws.send_json(heartbeats)
        while True:
            while (
                request.config_dict["rubintv/heartbeats"][location.slug]
                == heartbeats
            ):
                await asyncio.sleep(10)
            heartbeats = request.config_dict["rubintv/heartbeats"][
                location.slug
            ]
            await ws.send_json(heartbeats)
    finally:
        request.config_dict["websockets"].discard(ws)
        return ws


@routes.get("/{location}/admin", name="admin")
@template("admin.jinja")
async def get_admin_page(request: web.Request) -> Dict[str, Any]:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)
    services = request.config_dict["rubintv/models"].services
    loc_services = {name: services[name] for name in location.services}
    title = build_title(location.name, "Admin", request=request)
    return {
        "title": title,
        "location": location,
        "services": loc_services,
    }


@routes.post("/{location}/reload_historical")
async def reload_historical(request: web.Request) -> web.Response:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)
    historical = request.config_dict[f"rubintv/cached_data/{location.slug}"]
    historical.reload()
    return web.Response(text="OK", content_type="text/plain")


@routes.get("/summit/allsky")
@template("cameras/allsky.jinja")
async def get_all_sky_current(request: web.Request) -> Dict[str, Any]:
    locations = request.config_dict["rubintv/models"].locations
    location = locations["summit"]
    title = build_title("Summit", "All Sky", request=request)
    historical = request.config_dict["rubintv/cached_data/summit"]
    bucket = request.config_dict["rubintv/buckets/summit"]
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras["allsky"]
    image_channel = camera.channels["image"]
    current = get_current_event(camera, image_channel, bucket, historical)
    movie_channel = camera.channels["movie"]
    movie = get_current_event(camera, movie_channel, bucket, historical)
    return {
        "title": title,
        "location": location,
        "camera": camera,
        "current": current,
        "movie": movie,
    }


@routes.get("/summit/allsky/update/{channel}")
async def get_all_sky_current_update(request: web.Request) -> web.Response:
    historical = request.config_dict["rubintv/cached_data/summit"]
    bucket = request.config_dict["rubintv/buckets/summit"]
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras["allsky"]
    channel_name = request.match_info["channel"]

    if channel_name not in camera.channels:
        raise web.HTTPNotFound

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


@routes.get("/{location}/{camera}", name="camera")
async def get_recent_table(request: web.Request) -> web.Response:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)

    cam_name = request.match_info["camera"]
    if cam_name not in location.all_cameras():
        raise web.HTTPNotFound()
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras[cam_name]
    title = build_title(location.name, camera.name, request=request)

    logger = request["safir/logger"]
    with Timer() as timer:
        if not camera.online:
            context: Dict[str, Any] = {"location": location, "camera": camera}
            template = "cameras/not_online.jinja"
        else:
            bucket = request.config_dict[f"rubintv/buckets/{location_name}"]
            historical = request.config_dict[
                f"rubintv/cached_data/{location_name}"
            ]

            the_date, events = get_most_recent_day_events(
                bucket, camera, historical
            )

            night_reports_link = get_nights_report_link_type(
                camera, historical, the_date
            )

            metadata_json = get_metadata_json(bucket, camera, the_date)
            per_day = get_per_day_channels(bucket, camera, the_date)

            template = "cameras/camera.jinja"
            context = {
                "title": title,
                "location": location,
                "camera": camera,
                "date": the_date.strftime("%Y-%m-%d"),
                "events": events,
                "metadata": metadata_json,
                "night_reports_link": night_reports_link,
                "per_day": per_day,
                "viewer_link": get_image_viewer_link,
                "event_page_link": get_event_page_link,
            }
    logger.info("get_recent_table", duration=timer.seconds)
    response = render_template(template, request, context)
    return response


@routes.get("/{location}/{camera}/update")
async def update_todays_table(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        location_name = request.match_info["location"]
        location = find_location(location_name, request)

        cam_name = request.match_info["camera"]
        if cam_name not in location.all_cameras():
            raise web.HTTPNotFound()
        cameras = request.config_dict["rubintv/models"].cameras
        camera = cameras[cam_name]

        bucket = request.config_dict[f"rubintv/buckets/{location_name}"]
        historical = request.config_dict[
            f"rubintv/cached_data/{location_name}"
        ]

        the_date, events = get_most_recent_day_events(
            bucket, camera, historical
        )

        night_reports_link = get_nights_report_link_type(
            camera, historical, the_date
        )
        metadata_json = get_metadata_json(bucket, camera, the_date)
        per_day = get_per_day_channels(bucket, camera, the_date)

        context = {
            "location": location,
            "camera": camera,
            "date": the_date,
            "events": events,
            "metadata": metadata_json,
            "night_reports_link": night_reports_link,
            "per_day": per_day,
            "viewer_link": get_image_viewer_link,
            "event_page_link": get_event_page_link,
        }
        table_html = render_string(
            "cameras/data-table-header.jinja", request, context
        )
        per_day_html = render_string(
            "cameras/per-day-refresh.jinja", request, context
        )
        html_parts = {"table": table_html, "per_day": per_day_html}
        json_res = json.dumps(html_parts)
    logger.info("update_todays_table", duration=timer.seconds)
    return web.Response(text=json_res, content_type="application/json")


@routes.get("/{location}/{camera}/night_reports", name="night_reports")
@template("cameras/night-report.jinja")
async def get_night_reports(request: web.Request) -> dict[str, Any]:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)

    cam_name = request.match_info["camera"]
    if cam_name not in location.all_cameras():
        raise web.HTTPNotFound()
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras[cam_name]
    title = build_title(
        location.name, camera.name, "Night Reports", request=request
    )

    bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]
    day_obs = get_current_day_obs()

    plots: Dict[str, List[Night_Report_Event]] = {}
    dashboard_data: Dict[str, str] = {}
    if night_reports := get_night_report_events(bucket, camera, day_obs):
        plots, dashboard_data = night_reports
    plots_dict = {
        group: [plot.dict() for plot in plots[group]] for group in plots
    }
    reports_json = {"text": dashboard_data, "plots": plots_dict}

    return {
        "title": title,
        "location": location,
        "camera": camera,
        "date": day_obs,
        "plots": plots,
        "reports_json": reports_json,
        "dashboard_data": dashboard_data,
    }


@routes.get("/{location}/{camera}/night_reports/update/{date}")
async def update_night_reports(request: web.Request) -> web.Response:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)

    cam_name = request.match_info["camera"]
    if cam_name not in location.all_cameras():
        raise web.HTTPNotFound()
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras[cam_name]

    bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]

    date_str = request.match_info["date"]
    the_date = date_from_url_part(date_str)

    plots: Dict[str, List[Night_Report_Event]] = {}
    dashboard_data: Dict[str, str] = {}
    if night_reports := get_night_report_events(bucket, camera, the_date):
        plots, dashboard_data = night_reports

    plots_dict = {
        group: [plot.dict() for plot in plots[group]] for group in plots
    }
    text_html = render_string(
        "cameras/night-report-text.jinja",
        request,
        {"dashboard_data": dashboard_data},
    )
    reports_json = json.dumps({"text": text_html, "plots": plots_dict})

    return web.Response(text=reports_json, content_type="application/json")


@routes.get(
    "/{location}/{camera}/historical_night_reports/{date_str}",
    name="nr_history",
)
@template("cameras/night-report-historical.jinja")
async def get_historical_night_reports(request: web.Request) -> Dict[str, Any]:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)

    cam_name = request.match_info["camera"]
    if cam_name not in location.all_cameras():
        raise web.HTTPNotFound()
    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras[cam_name]

    historical: HistoricalData = request.config_dict[
        f"rubintv/cached_data/{location.slug}"
    ]

    date_str = request.match_info["date_str"]
    the_date = date_from_url_part(date_str)

    title = build_title(
        location.name,
        camera.name,
        "Historical Night Reports",
        date_str,
        request=request,
    )

    plots: Dict[str, List[Night_Report_Event]] = {}
    dashboard_data: Dict[str, str] = {}
    if night_reports := historical.get_night_reports_for(camera, the_date):
        bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]
        plots, dashboard_data = download_sort_night_report_events(
            bucket, night_reports
        )

    plots_dict = {
        group: [plot.dict() for plot in plots[group]] for group in plots
    }
    reports_json = json.dumps({"text": dashboard_data, "plots": plots_dict})

    return {
        "title": title,
        "location": location,
        "camera": camera,
        "date": the_date,
        "plots": plots,
        "dashboard_data": dashboard_data,
        "reports_json": reports_json,
    }


@routes.get("/summit/allsky/historical")
@template("cameras/allsky-historical.jinja")
async def get_allsky_historical(request: web.Request) -> Dict[str, Any]:
    locations = request.config_dict["rubintv/models"].locations
    location = locations["summit"]
    title = build_title("Summit", "All Sky", "Historical", request=request)
    historical = request.config_dict["rubintv/cached_data/summit"]
    logger = request["safir/logger"]

    with Timer() as timer:
        cameras = request.config_dict["rubintv/models"].cameras
        camera = cameras["allsky"]

        years = historical.get_camera_calendar(camera)
        most_recent_year = next(iter(years.keys()))

        channel = camera.channels["movie"]
        movie = historical.get_most_recent_event(camera, channel)

    logger.info("get_allsky_historical", duration=timer.seconds)
    return {
        "title": title,
        "location": location,
        "camera": camera,
        "year_to_display": most_recent_year,
        "years": years,
        "month_names": month_names(),
        "calendar": calendar_factory(),
        "movie": movie,
        "get_date": date,
    }


@routes.get("/summit/allsky/historical/{date_str}")
@template("cameras/allsky-historical.jinja")
async def get_allsky_historical_movie(request: web.Request) -> Dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        locations = request.config_dict["rubintv/models"].locations
        location = locations["summit"]
        cameras = request.config_dict["rubintv/models"].cameras
        camera = cameras["allsky"]
        historical = request.config_dict["rubintv/cached_data/summit"]

        date_str = request.match_info["date_str"]
        title = build_title(
            "Summit", "All Sky", "Historical", date_str, request=request
        )

        the_date = date_from_url_part(date_str)
        year = the_date.year

        all_events: Dict[str, List[Event]] = historical.get_events_for_date(
            camera, the_date
        )
        # check if any events in the arrays in the dict
        if not [v for values in all_events.values() for v in values]:
            raise web.HTTPNotFound

        years = historical.get_camera_calendar(camera)
        movie = all_events["movie"][0]
    logger.info("get_allsky_historical_movie", duration=timer.seconds)
    return {
        "title": title,
        "location": location,
        "camera": camera,
        "years": years,
        "year_to_display": year,
        "month_names": month_names(),
        "calendar": calendar_factory(),
        "movie": movie,
        "get_date": date,
    }


@routes.get("/{location}/{camera}/historical", name="historical")
@template("cameras/historical.jinja")
async def get_historical(request: web.Request) -> Dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        location_name = request.match_info["location"]
        location = find_location(location_name, request)

        bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]
        cameras = request.config_dict["rubintv/models"].cameras
        camera = cameras[request.match_info["camera"]]
        title = build_title(
            location.name, camera.name, "Historical", request=request
        )
        historical = request.config_dict[
            f"rubintv/cached_data/{location.slug}"
        ]
        active_years = historical.get_years(camera)
        reverse_years = sorted(active_years, reverse=True)
        year_to_display = reverse_years[0]

        years = historical.get_camera_calendar(camera)

        day_obs = historical.get_most_recent_day(camera)
        mrd_dict = historical.get_events_for_date(camera, day_obs)
        metadata_json = get_metadata_json(bucket, camera, day_obs)
        mrd_events = make_table_rows_from_columns_by_seq(
            mrd_dict, metadata_json
        )

        per_day = get_per_day_channels(bucket, camera, day_obs)
        night_reports_link = ""
        if historical.get_night_reports_for(camera, day_obs):
            night_reports_link = "historical"

    logger.info("get_historical", duration=timer.seconds)
    return {
        "title": title,
        "location": location,
        "camera": camera,
        "year_to_display": year_to_display,
        "years": years,
        "month_names": month_names(),
        "calendar": calendar_factory(),
        "date": day_obs,
        "events": mrd_events,
        "metadata": metadata_json,
        "per_day": per_day,
        "night_reports_link": night_reports_link,
        "viewer_link": get_image_viewer_link,
        "event_page_link": get_event_page_link,
        "get_date": date,
    }


@routes.get("/{location}/{camera}/historical/{date_str}", name="hist_single")
@template("cameras/historical.jinja")
async def get_historical_day_data(request: web.Request) -> Dict[str, Any]:
    location_name = request.match_info["location"]
    location = find_location(location_name, request)

    historical: HistoricalData = request.config_dict[
        f"rubintv/cached_data/{location.slug}"
    ]
    bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]

    cameras = request.config_dict["rubintv/models"].cameras
    camera = cameras[request.match_info["camera"]]
    date_str = request.match_info["date_str"]

    the_date = date_from_url_part(date_str)
    title = build_title(
        location.slug, camera.name, "Historical", date_str, request=request
    )

    day_dict = historical.get_events_for_date(camera, the_date)
    # check if any events in the arrays in the dict
    if not [v for values in day_dict.values() for v in values]:
        raise web.HTTPNotFound

    metadata_json = get_metadata_json(bucket, camera, the_date)
    day_events = make_table_rows_from_columns_by_seq(day_dict, metadata_json)
    night_reports_link = ""
    if historical.get_night_reports_for(camera, the_date):
        night_reports_link = "historical"

    years = historical.get_camera_calendar(camera)

    per_day = get_per_day_channels(bucket, camera, the_date)
    return {
        "title": title,
        "location": location,
        "camera": camera,
        "years": years,
        "year_to_display": the_date.year,
        "month_names": month_names(),
        "calendar": calendar_factory(),
        "date": the_date,
        "events": day_events,
        "metadata": metadata_json,
        "per_day": per_day,
        "night_reports_link": night_reports_link,
        "viewer_link": get_image_viewer_link,
        "event_page_link": get_event_page_link,
        "get_date": date,
    }


@routes.get("/{location}/{camera}/{channel}/event/{date}/{seq}", name="single")
@template("single_event.jinja")
async def events(request: web.Request) -> Dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        location_name = request.match_info["location"]
        location = find_location(location_name, request)
        bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]
        cameras = request.config_dict["rubintv/models"].cameras
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
        "location": location,
        "camera": camera,
        "channel": channel.name,
        "event": event,
        "date": the_date,
        "seq": seq,
    }


@routes.get("/{location}/{camera}/{channel}_current", name="current")
@template("current.jinja")
async def current(request: web.Request) -> Dict[str, Any]:
    logger = request["safir/logger"]
    with Timer() as timer:
        location_name = request.match_info["location"]
        location = find_location(location_name, request)
        cameras = request.config_dict["rubintv/models"].cameras
        camera = cameras[request.match_info["camera"]]
        bucket = request.config_dict[f"rubintv/buckets/{location.slug}"]
        historical = request.config_dict[
            f"rubintv/cached_data/{location.slug}"
        ]
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
        "location": location,
        "camera": camera,
        "event": event,
        "channel": channel.name,
        "date": the_date,
        "seq": seq,
    }
