"""Handlers for rubintv endpoints."""

__all__ = [
    "get_page"
    "get_table",
    # "events",
    # "current",
]

from asyncio.log import logger
from datetime import datetime
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

channels = {
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
    # "rollingbuffer": Channel(
    #     name="Rolling Buffer",
    #     prefix="rolling_buffer",
    #     endpoint="rollingbuffer"
    # ),
    # "movie": Channel(
    #     name="Tonight's Movie",
    #     prefix="movie",
    #     endpoint="movie"
    # )
}

@routes.get("")
@routes.get("/")
async def get_page(request: web.Request) -> web.Response:
    page = get_formatted_page("home.jinja", title="Rubin TV Display", telescopes=telescopes)
    return web.Response(text=page, content_type="text/html")

@routes.get("/{telescope}")
async def get_table(request: web.Request) -> web.Response:
    telescope = telescopes[request.match_info["telescope"]]
    logger = request["safir/logger"]
    with Timer() as timer:
        if "num" in request.query:
            num = int(request.query["num"])
        else:
            num = 36
        if "beg_date" in request.query and request.query["beg_date"]:
            beg_date = datetime.fromisoformat(request.query["beg_date"])
        else:
            beg_date = None
        if "end_date" in request.query and request.query["end_date"]:
            end_date = datetime.fromisoformat(request.query["end_date"])
        else:
            end_date = None
        bucket = request.config_dict["rubintv/gcs_bucket"]
        page = get_formatted_table(
            f'telescopes/{telescope.slug}.jinja', telescope, bucket, num=num, beg_date=beg_date, end_date=end_date
        )
    logger.info("get_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{telescope}/{channel}events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        page = get_single_event_page(
            request, channels[request.match_info["channel"]]
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
        page = get_formatted_page2(
            "current.html",
            channels[request.match_info["name"]].prefix,
            bucket,
            num=1,
        )
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")

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

def get_formatted_table(
    template: str,
    telescope: Telescope,
    bucket: Bucket,
    num: int = None,
    beg_date: datetime = None,
    end_date: datetime = None,
) -> str:
    imgs = {}
    if beg_date or end_date:
        for chan in channels:
            imgs[chan] = timeWindowSort(
                bucket,
                channels[chan].prefix,
                num,
                beg_date=beg_date,
                end_date=end_date,
            )
    else:
        for chan in channels:
            imgs[chan] = get_image_list(bucket, channels[chan].prefix, num)
    keys = list(imgs.keys())
    for i, img in enumerate(
        imgs["monitor"]
    ):  # I know there will always be a monitor style image
        imgs["monitor"][i].chans.append(channels["monitor"])
        for k in keys:
            if k == "monitor":
                continue
            match = False
            for mim in imgs[k]:
                if img.cleanDate() == mim.cleanDate() and img.seq == mim.seq:
                    imgs["monitor"][i].chans.append(channels[k])
                    match = True
                    break
            if not match:
                # Ignore typing here since the template expects None if there
                imgs["monitor"][i].chans.append(None)

    env = Environment(
        loader=PackageLoader("rubintv"),
        autoescape=select_autoescape()
    )
    env.globals.update(zip=zip)
    templ = env.get_template(template)
    return templ.render(
        channels=channels,
        imgs=imgs["monitor"],
        telescope=telescope
    )


def get_formatted_page2(
    template: str,
    prefix: str,
    bucket: Bucket,
    num: int = None,
    date: str = None,
    seq: str = None,
    **kwargs: str,
) -> str:
    if num:
        imgs = get_image_list(bucket, prefix, num)
    elif date and seq:
        imgs = find_event(bucket, prefix, date, seq)
    else:
        raise ValueError("num or (date and seq) must be provided")
    env = Environment(
        loader=PackageLoader("rubintv"),
        autoescape=select_autoescape()
    )
    templ = env.get_template(template)
    return templ.render(imgs=imgs, **kwargs)


def find_event(
    bucket: Bucket, prefix: str, date: str, seq: str
) -> List[Image]:
    imgs = get_image_list(bucket, prefix)
    for img in imgs:
        if img.cleanDate() == date and img.seq == int(seq):
            return [
                img,
            ]
    raise ValueError(f"No event found for date={date} and sequence={seq}")


def get_image_list(
    bucket: Bucket, prefix: str, num: Optional[int] = 25
) -> List[Image]:
    blobs = bucket.list_blobs(max_results=num, prefix=prefix)
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
