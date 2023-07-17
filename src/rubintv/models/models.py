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
    bucket_name: str = ""
    camera_name: str = ""
    channel_name: str = ""
    #

    def __post_init__(self) -> None:
        self.name, self.day_obs, self.seq_num = self.parse_url()

    def parse_url(self) -> tuple:
        """Parses the object URL.

        Returns
        -------
        url_parts: `tuple`

        Raises
        ------
        EventInitialisationError
            Thrown if any part of the parsing process breaks.
        """
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


def build_prefix_with_date(camera: Camera, day_obs: date) -> str:
    camera_name = camera.name
    # eventually the prefix will be formed something like:
    # return f"{location_name}/{camera_name}/{day_obs}/{channel_name}"
    return f"{camera_name}_monitor/{camera_name}-monitor_dayObs_{day_obs}"


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
