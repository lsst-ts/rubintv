"""Handlers for rubintv endpoints."""

__all__ = [
    "get_table",
    "imevents",
    "specevents",
    "imcurrent",
    "speccurrent",
]

from typing import List, Optional

from aiohttp import web
from google.cloud.storage import Bucket
from jinja2 import Environment, PackageLoader, select_autoescape

from rubintv.handlers import routes
from rubintv.models import Image


@routes.get("")
@routes.get("/")
async def get_table(request: web.Request) -> web.Response:
    """"""
    if "num" in request.query:
        num = int(request.query["num"])
    else:
        num = 10
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_table("table.html", bucket, num=num)
    return web.Response(text=page, content_type="text/html")


@routes.get("/imevents/{date}/{seq}")
async def imevents(request: web.Request) -> web.Response:
    page = get_event_page(request, "summit_imexam")
    return web.Response(text=page, content_type="text/html")


@routes.get("/specevents/{date}/{seq}")
async def specevents(request: web.Request) -> web.Response:
    page = get_event_page(request, "summit_specexam")
    return web.Response(text=page, content_type="text/html")


def get_event_page(request: web.Request, prefix: str) -> str:
    date = request.match_info["date"]
    seq = request.match_info["seq"]
    bucket = request.config_dict["rubintv/gcs_bucket"]
    return get_formatted_page("data.html", prefix, bucket, date=date, seq=seq)


@routes.get("/im_current")
async def imcurrent(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_page("current.html", "summit_imexam", bucket, num=1)
    return web.Response(text=page, content_type="text/html")


@routes.get("/spec_current")
async def speccurrent(request: web.Request) -> web.Response:
    bucket = request.config_dict["rubintv/gcs_bucket"]
    page = get_formatted_page("current.html", "summit_specexam", bucket, num=1)
    return web.Response(text=page, content_type="text/html")


def get_formatted_table(
    template: str,
    bucket: Bucket,
    num: int = None,
) -> str:
    imimgs = timeSort(bucket, "summit_imexam", num)
    specimgs = timeSort(bucket, "summit_specexam", num)
    trimmed_specims = []
    for img in imimgs:
        match = False
        for simg in specimgs:
            if img.cleanDate() == simg.cleanDate() and img.seq == simg.seq:
                trimmed_specims.append(simg)
                match = True
                break
        if not match:
            # Ignore typing here since the template expects None if there
            # is no spec image for this run
            trimmed_specims.append(None)  # type: ignore[arg-type]

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
        imimgs=imimgs,
        specimgs=trimmed_specims,
        imimg_attr1="date",
        imimg_attr2="seq",
        specimg_attr1="date",
        specimg_attr2="date",
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
    sblobs = sorted(blobs, key=lambda x: x.time_created, reverse=True)
    clean_URLs = [
        el.public_url for el in sblobs if el.public_url.endswith(".png")
    ]

    if num:
        return [Image(p) for p in clean_URLs][:num]
    return [Image(p) for p in clean_URLs]
