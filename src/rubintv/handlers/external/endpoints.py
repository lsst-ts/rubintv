"""Handlers for rubintv endpoints."""

__all__ = [
    "get_table",
    "events",
    "current",
]

from datetime import datetime
from typing import List, Optional

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import Channel, Image
from rubintv.timer import Timer

channels = {
    "spec": Channel(
        name="SpecExamine", prefix="summit_specexam", endpoint="specevents"
    ),
    "im": Channel(
        name="ImExamine", prefix="summit_imexam", endpoint="imevents"
    ),
    "mount": Channel(
        name="AuxtelTorques",
        prefix="auxtel_mount_torques",
        endpoint="mountevents",
    ),
    "monitor": Channel(
        name="AuxtelMonitor",
        prefix="auxtel_monitor",
        endpoint="monitorevents",
    ),
}


@routes.get("")
@routes.get("/")
async def get_table(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        if "num" in request.query:
            num = int(request.query["num"])
        else:
            num = 50
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
            "table.html", bucket, num=num, beg_date=beg_date, end_date=end_date
        )
    logger.info("get_table", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


@routes.get("/{name}events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        page = get_event_page(
            request, channels[request.match_info["name"]].prefix
        )
    logger.info("events", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_event_page(request: web.Request, prefix: str) -> str:
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    return get_formatted_page("data.html", prefix, bucket, date=date, seq=seq)


@routes.get("/{name}_current")
async def current(request: web.Request) -> web.Response:
    logger = request["safir/logger"]
    with Timer() as timer:
        bucket = request.config_dict["rubintv/gcs_bucket"]
        page = get_formatted_page(
            "current.html",
            channels[request.match_info["name"]].prefix,
            bucket,
            num=1,
        )
    logger.info("current", duration=timer.seconds)
    return web.Response(text=page, content_type="text/html")


def get_formatted_table(
    template: str,
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
            imgs[chan] = timeSort(bucket, channels[chan].prefix, num)
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
        loader=PackageLoader("rubintv", "templates"),
        autoescape=select_autoescape(
            [
                "html",
            ]
        ),
    )
    env.globals.update(zip=zip)
    templ = env.get_template(template)
    return templ.render(
        ncols=len(channels),
        imgs=imgs["monitor"],
    )


def get_formatted_page(
    template: str,
    prefix: str,
    bucket: Bucket,
    num: int = None,
    date: str = None,
    seq: str = None,
    **kwargs: str,
) -> str:
    if num:
        imgs = timeSort(bucket, prefix, num)
    elif date and seq:
        imgs = find_event(bucket, prefix, date, seq)
    else:
        raise ValueError("num or (date and seq) must be provided")
    env = Environment(
        loader=PackageLoader("rubintv", "templates"),
        autoescape=select_autoescape(
            [
                "html",
            ]
        ),
    )
    templ = env.get_template(template)
    return templ.render(imgs=imgs, **kwargs)


def find_event(
    bucket: Bucket, prefix: str, date: str, seq: str
) -> List[Image]:
    imgs = timeSort(bucket, prefix)
    for img in imgs:
        if img.cleanDate() == date and img.seq == int(seq):
            return [
                img,
            ]
    raise ValueError(f"No event found for date={date} and sequence={seq}")


def timeSort(
    bucket: Bucket, prefix: str, num: Optional[int] = None
) -> List[Image]:
    blobs = bucket.list_blobs(prefix=prefix)
    imgs = [
        Image(el.public_url) for el in blobs if el.public_url.endswith(".png")
    ]
    simgs = sorted(imgs, key=lambda x: (x.date, x.seq), reverse=True)

    if num:
        return simgs[:num]
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
