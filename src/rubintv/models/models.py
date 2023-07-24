"""Models for rubintv."""

import re
from datetime import date, datetime, timedelta
from typing import Any, Type

from dateutil.tz import gettz
from pydantic import BaseModel, field_validator
from pydantic.dataclasses import dataclass

__all__ = [
    "Location",
    "Channel",
    "Camera",
    "Heartbeat",
    "Event",
    "EventInitialisationError",
    "get_current_day_obs",
    "build_prefix_with_date",
]


class Channel(BaseModel):
    name: str
    title: str
    prefix: str
    label: str = ""
    service_dependency: str = ""


class Camera(BaseModel):
    name: str
    title: str
    online: bool
    metadata_slug: str = ""
    logo: str = ""
    image_viewer_link: str = ""
    channels: list[Channel] | None = None
    per_day_channels: list[Channel] | None = None
    night_report_prefix: str = ""
    night_report_label: str = "Night Report"
    metadata_cols: dict[str, dict[str, str]] | dict[str, str] | None = None
    js_entry: str = ""

    # If metadata_slug/js_entry not set, use name as default
    @field_validator("metadata_slug", "js_entry")
    def default_as_name(cls: Type, v: str, values: Any) -> str:
        return v or values.get("name")


class Location(BaseModel, arbitrary_types_allowed=True):
    name: str
    title: str
    bucket_name: str
    services: list[str]
    camera_groups: dict[str, list[str]]
    cameras: list[Camera] = []
    logo: str = ""


class Heartbeat(BaseModel):
    name: str
    title: str
    channels_as_cam_name: str = ""
    channels: None | list[Channel] = None
    services: dict[str, str] = {}


class EventInitialisationError(RuntimeError):
    pass


@dataclass
class Event:
    url: str
    hash: str
    # derived fields:
    name: str = ""
    camera_name: str = ""
    day_obs: date = date(1970, 1, 1)
    channel_name: str = ""
    seq_num: int | str = 0
    ext: str = ""

    def __post_init__(self) -> None:
        (
            self.name,
            self.camera_name,
            self.day_obs,
            self.channel_name,
            self.seq_num,
            self.ext,
        ) = self.parse_url()

    def parse_url(self) -> tuple:
        """Parses the object URL.

        URL is as ``f"{camera}/{date_str}/{channel}/{seq:06}.{ext}"``.
        There should only be one dot (.) which should precede the extension.

        Returns
        -------
        url_parts: `tuple`

        Raises
        ------
        EventInitialisationError
            Thrown if any part of the parsing process breaks.
        """
        url = self.url
        name_re = re.compile(r"\w+\/[\d-]+\/\w+\/(\d{6}|final)\.\w+$")
        if match := name_re.match(url):
            name = match.group()
        else:
            raise EventInitialisationError(f"url can't be parsed: {url}")

        rest, ext = name.split(".")
        parts = rest.split("/")
        # parts == [camera, date_str, channel, seq]
        camera = parts.pop(0)

        day_obs_str = parts.pop(0)
        y, m, d = day_obs_str.split("-")
        try:
            day_obs = date(int(y), int(m), int(d))
        except ValueError:
            raise EventInitialisationError(
                f"date can't be parsed: {day_obs_str}"
            )

        channel = parts.pop(0)

        seq_num: str | int = parts.pop()
        if seq_num != "final":
            seq_num = int(seq_num)

        return (name, camera, day_obs, channel, seq_num, ext)


def build_prefix_with_date(camera: Camera, day_obs: date) -> str:
    camera_name = camera.name
    prefix = f"{camera_name}/{day_obs}/"
    return prefix


def get_current_day_obs() -> date:
    """Get the current day_obs.

    The observatory rolls the date over at UTC minus 12 hours.

    Returns
    -------
    dayObs : `date`
        The current observation day.
    """
    utc = gettz("UTC")
    nowUtc = datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs
