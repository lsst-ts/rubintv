"""Models for rubintv."""

import re
from datetime import date
from typing import Any, Type

from pydantic import BaseModel, validator
from pydantic.dataclasses import dataclass

__all__ = [
    "Location",
    "Channel",
    "Camera",
    "Heartbeat",
    "Event",
    "EventInitialisationError",
]


class Location(BaseModel):
    name: str
    title: str
    bucket: str
    services: list[str]
    camera_groups: dict[str, list[str]]
    logo: str = ""


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
    channels: list[Channel] | None
    per_day_channels: list[Channel] | None
    night_report_prefix: str = ""
    night_report_label: str = "Night Report"
    metadata_cols: dict[str, dict[str, str]] | dict[str, str] | None
    js_entry: str = ""

    # If metadata_slug/js_entry not set, use name as default
    @validator("metadata_slug", "js_entry", pre=True, always=True)
    def default_as_name(cls: Type, v: str, values: Any) -> str:
        return v or values.get("name")


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
    day_obs: date = date.today()
    seq_num: int | str = 0
    #
    location: Location | None = None
    camera: Camera | None = None
    channel: Channel | None = None

    def __post_init__(self) -> None:
        self.name, self.day_obs, self.seq_num = self.parse_url()

    def parse_url(self) -> tuple:
        url = self.url
        name_re = re.compile(r"^http[s]:\/\/[\w*\.]+\/[\w*\.]+\/")
        if match := name_re.match(url):
            name = url[match.end() :]
        else:
            raise EventInitialisationError(url)
        date_re = re.compile(r"dayObs_([\d-]+)")
        if match := date_re.search(url):
            day_obs_str = match.group(1)
        else:
            raise EventInitialisationError()
        y, m, d = day_obs_str.split("-")
        try:
            day_obs = date(int(y), int(m), int(d))
        except ValueError:
            raise EventInitialisationError(url)
        if not url.rfind("seqNum_final") == -1:
            seq_num: str | int = "final"
        else:
            seq_re = re.compile(r"seqNum_(\d+)")
            if match := seq_re.search(url):
                seq_num = int(match.group(1))
            else:
                raise EventInitialisationError(url)
        return (name, day_obs, seq_num)
