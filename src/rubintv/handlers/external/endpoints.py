"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page"
    "get_table",
    # "events",
    # "current",
]

from asyncio.log import logger
from datetime import datetime, date, timedelta
from typing import List, Optional
from unicodedata import name

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import Channel, Image, Telescope
from rubintv.timer import Timer


telescopes = {
    "auxtel": Telescope(
        name="Auxtel", slug="auxtel", online=True
    ),
    "comcam": Telescope(
        name="Comcam", slug="comcam", online=False
    ),
    "lsstcam": Telescope(
        name="LSSTcam", slug="lsstcam", online=False
    ),
}

per_image_channels = {
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
    page = get_formatted_page("home.jinja", title="Rubin TV Display", telescopes=telescopes)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{telescope}")
async def get_recent_table(request: web.Request) -> web.Response:
    telescope = telescopes[request.match_info["telescope"]]
    logger = request["safir/logger"]
    with Timer() as timer:
        # if "num" in request.query:
        #     num = int(request.query["num"])
        # else:
        #     num = 36
        # if "beg_date" in request.query and request.query["beg_date"]:
        #     beg_date = datetime.fromisoformat(request.query["beg_date"])
        # else:
        #     beg_date = None
        # if "end_date" in request.query and request.query["end_date"]:
        #     end_date = datetime.fromisoformat(request.query["end_date"])
        # else:
        #     end_date = None
        bucket = request.config_dict["rubintv/gcs_bucket"]
        imgs = get_most_recent_day_images(bucket)
        page = get_formatted_page(
            f'telescopes/layout.jinja', telescope=telescope, channels=per_image_channels,
            # date=date.today(),
            date=imgs[0].cleanDate(), imgs=imgs
        )
    logger.info("get_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{telescope}/historical")
async def get_historical_table(request: web.Request) -> web.Response:
    return

@routes.get("/{telescope}/{channel}events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        page = get_single_event_page(
            request, per_image_channels[request.match_info["channel"]]
        )
    logger.info("events", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_single_event_page(request: web.Request, channel: Channel) -> str:
    # telescope = request.match_info["telescope"]
    prefix = channel.prefix
    prefix_dashes = prefix.replace("_", "-")
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    img = Image(f"https://storage.googleapis.com/{bucket.name}/{prefix}/{prefix_dashes}_dayObs_{date}_seqNum_{seq}.png")
    return get_formatted_page("single_event.jinja", img=img, prefix=channel.css_class)


@routes.get("/{telescope}/{name}_current")
async def current(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        channel = per_image_channels[request.match_info["name"]]
        page = get_current_event(
            channel.prefix,
            bucket,
            channel.css_class
        )
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_current_event(
    prefix: str,
    bucket: Bucket,
    channel_name: str
) -> str:
    imgs = get_image_list(bucket, prefix, 1)
    if imgs:
        return get_formatted_page("current.jinja", img=imgs[0], channel=channel_name)
    raise ValueError(f"No current event found for prefix={prefix}")


def get_image_list(bucket: Bucket, prefix: str, num: Optional[int] = None) -> List[Image]:
    blobs = bucket.list_blobs(prefix=prefix)
    simgs = get_sorted_images_from_blobs(blobs)
    if num:
        return simgs[:num]
    return simgs


def get_monitor_prefix_from_date(a_date):
  return f"auxtel_monitor/auxtel-monitor_dayObs_{a_date}"

def get_most_recent_day_images(bucket: Bucket) -> List[Image]:
    try_date = date.today()
    timer = datetime.now()
    timeout = 2
    blobs = []
    while not blobs:
        try_date = try_date - timedelta(1) #no blobs? try the day defore
        prefix = get_monitor_prefix_from_date(try_date)
        blobs = list(bucket.list_blobs(prefix=prefix))
        elapsed = datetime.now() - timer
        if elapsed.seconds > timeout:
            raise TimeoutError(f"Timed out. Couldn't find most recent day's records within {timeout} seconds")
        imgs = {}
        imgs['monitor'] = get_sorted_images_from_blobs(blobs)

        for chan in per_image_channels.keys():
            if chan == 'monitor': continue
            prefix = per_image_channels[chan].prefix
            prefix_dashes = prefix.replace("_", "-")
            new_prefix = f"{prefix}/{prefix_dashes}_dayObs_{try_date}_seqNum_"
            blobs = list(bucket.list_blobs(prefix=new_prefix))
            imgs[chan] = get_sorted_images_from_blobs(blobs)

        keys = list(imgs.keys())
        for i, img in enumerate(
            imgs["monitor"]
        ):  # I know there will always be a monitor style image
            imgs["monitor"][i].chans.append(per_image_channels["monitor"])
            for k in keys:
                if k == "monitor": continue
                match = False
                for mim in imgs[k]:
                    if img.seq == mim.seq:
                        imgs["monitor"][i].chans.append(per_image_channels[k])
                        match = True
                        imgs[k].remove(mim)
                        break
                if not match:
                    # Ignore typing here since the template expects None if not there
                    imgs["monitor"][i].chans.append(None)
    return imgs['monitor']


def get_sorted_images_from_blobs(blobs: List)->List[Image]:
    imgs = [
        Image(el.public_url) for el in blobs if el.public_url.endswith(".png")
    ]
    simgs = sorted(imgs, key=lambda x: (x.date, x.seq), reverse=True)
    return simgs


def timeWindowSort(
    bucket: Bucket,
    prefix: str,
    num: Optional[int] = None,
    beg_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Image]:
    imgs = timeSort(bucket, prefix)
    if beg_date and end_date:
        simgs = [
            el for el in imgs if beg_date < el.date and end_date > el.date
        ]
    elif beg_date:
        simgs = [el for el in imgs if beg_date < el.date]
    elif end_date:
        simgs = [el for el in imgs if end_date > el.date]
    else:
        raise RuntimeError(f"Something went wrong: {beg_date} and {end_date}")

    if num:
        return simgs[:num]
    return simgs

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
