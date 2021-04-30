"""Handlers for rubintv endpoints."""

__all__ = [
    "get_default_table",
    "get_table",
    "events",
    "current",
]

from typing import List, Optional

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import Image


@routes.get("/table")
async def get_default_table(request: web.Request) -> web.Response:
    """"""
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_table(
        "table.html", bucket, num=10, img_attr1="date", img_attr2="seq"
    )
    return web.Response(text=page, content_type="text/html")


@routes.get("/table/{num}")
async def get_table(request: web.Request) -> web.Response:
    """"""
    num = request.match_info["num"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_table(
        "table.html", bucket, num=int(num), img_attr1="date", img_attr2="seq"
    )
    return web.Response(text=page, content_type="text/html")


@routes.get("/events/{date}/{seq}")
async def events(request: web.Request) -> web.Response:
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_table("data.html", bucket, date=date, seq=seq)
    return web.Response(text=page, content_type="text/html")


@routes.get("/current")
async def current(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_table("current.html", bucket, num=1)
    return web.Response(text=page, content_type="text/html")


def get_formatted_table(
    template: str,
    bucket: Bucket,
    num: int = None,
    date: str = None,
    seq: str = None,
    **kwargs: str,
) -> str:
    if num:
        imgs = timeSort(bucket, num)
    elif date and seq:
        imgs = find_event(bucket, date, seq)
    else:
        raise ValueError("num or (date and seq) must be profided")
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


def find_event(bucket: Bucket, date: str, seq: str) -> List[Image]:
    imgs = timeSort(bucket)
    for img in imgs:
        if img.cleanDate() == date and img.seq == int(seq):
            return [
                img,
            ]
    raise ValueError(f"No event found for date={date} and sequence={seq}")


def timeSort(bucket: Bucket, num: Optional[int] = None) -> List[Image]:
    blobs = bucket.list_blobs(prefix="summit_imexam")
    sblobs = sorted(blobs, key=lambda x: x.time_created)
    clean_URLs = [
        el.public_url for el in sblobs if el.public_url.endswith(".png")
    ]

    return [Image(p) for p in clean_URLs]
