"""Models for rubintv."""
import re
from datetime import date, datetime, timedelta
from typing import Any, Type

from dateutil.tz import gettz
from pydantic import BaseModel, field_validator
from pydantic.dataclasses import dataclass
from typing_extensions import NotRequired, TypedDict

__all__ = [
    "Location",
    "Channel",
    "Camera",
    "Event",
    "get_current_day_obs",
    "build_prefix_with_date",
]


class Channel(BaseModel):
    name: str
    title: str
    label: str = ""
    per_day: bool = False


class Camera(BaseModel):
    name: str
    title: str
    online: bool
    metadata_from: str = ""
    logo: str = ""
    image_viewer_link: str = ""
    channels: list[Channel] = []
    night_report_prefix: str = ""
    night_report_label: str = "Night Report"
    metadata_cols: dict[str, dict[str, str]] | dict[str, str] | None = None
    js_entry: str = ""

    # If metadata_from/js_entry not set, use name as default
    @field_validator("metadata_from", "js_entry")
    def default_as_name(cls: Type, v: str, values: Any) -> str:
        return v or values.get("name")

    def seq_channels(self) -> list[Channel]:
        return [c for c in self.channels if not c.per_day]

    def pd_channels(self) -> list[Channel]:
        return [c for c in self.channels if c.per_day]


class Location(BaseModel, arbitrary_types_allowed=True):
    name: str
    title: str
    bucket_name: str
    camera_groups: dict[str, list[str]]
    cameras: list[Camera] = []
    logo: str = ""


@dataclass
class Event:
    key: str
    hash: str = ""
    # derived fields:
    camera_name: str = ""
    day_obs: str = ""
    channel_name: str = ""
    seq_num: int | str = ""
    filename: str = ""
    ext: str = ""
    url: str = ""

    def __post_init__(self) -> None:
        (
            self.camera_name,
            self.day_obs,
            self.channel_name,
            self.seq_num,
            self.filename,
            self.ext,
        ) = self.parse_key()

    def parse_key(self) -> tuple:
        """Parses a channel event object's key.

        A key is as:
        ``f"{camera}/{date_str}/{channel}/{seq:06}/{filename}.{ext}"``

        Returns
        -------
        url_parts: `tuple`
        """
        key = self.key
        name_re = re.compile(
            r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)\.(\w+)$"
        )
        if match := name_re.match(key):
            parts = match.groups()
        else:
            raise ValueError(f"Key can't be parsed: {key}")

        camera, day_obs_str, channel, seq_num, filename, ext = parts

        try:
            self.date_str_to_date(day_obs_str)
        except ValueError:
            raise ValueError(f"Date can't be parsed: {key}")

        if seq_num != "final":
            seq_num = int(seq_num)

        return (camera, day_obs_str, channel, seq_num, filename, ext)

    def date_str_to_date(self, date_str: str) -> date:
        y, m, d = date_str.split("-")
        return date(int(y), int(m), int(d))

    def day_obs_date(self) -> date:
        return self.date_str_to_date(self.day_obs)

    def seq_num_force_int(self) -> int:
        return self.seq_num if isinstance(self.seq_num, int) else -1


@dataclass
class NightReport:
    """Wrapper for a night report blob.

        -   Night Reports can be located in a given bucket using the prefix:
            ``f"/{camera_name}/{date_str}/night_report/"``.

        -   Plots take the form:
            ``f"/{camera_name}/{date_str}/night_report/{group}/{filename}.{ext}"``.

        -   Metadata takes the form:
             ``f"/{camera_name}/{date_str}/night_report/{filename}_md.json"``.


    Parameters
    ----------
    key: `str`
        The name used to find the object in the bucket.
    hash: `str`
        The md5 hash of the blob. This is used to keep plot images up-to-date
        onsite.
    camera: `str`
        The name of the camera the report belongs to.
    day_obs: `str`
        A hyphenated string representing the date i.e. ``"2023-12-31"``
    group: `str`
        The name of the group the data belogs to. In the case the file is
        metadata, the group is set as ``"metadata"``
    filename: `str`
        The fully qualified name of the plot or text item of data.
    ext: `str`
        The file extension.
    """

    key: str
    hash: str
    # derived fields
    camera: str = ""
    day_obs: str = ""
    group: str = ""
    filename: str = ""
    ext: str = ""

    def parse_key(self) -> tuple:
        """Split the filename into parts.

        Returns
        -------
        `tuple`
             Tuple of values used by `__post_init__` to fully init the object.
        """
        key = self.key
        metadata_re = re.compile(
            r"(\w+)\/([\d-]+)\/night_report\/([\w-]+_md)\.(\w+)$"
        )
        if match := metadata_re.match(key):
            parts = match.groups()
            camera, day_obs_str, filename, ext = parts
            group = "metadata"
        else:
            plot_re = re.compile(
                r"(\w+)\/([\d-]+)\/night_report\/([\w-]+)\/([\w-]+)\.(\w+)$"
            )
            if match := plot_re.match(key):
                parts = match.groups()
                camera, day_obs_str, group, filename, ext = parts
            else:
                raise ValueError(f"Key can't be parsed: {key}")

        return (camera, day_obs_str, group, filename, ext)

    def __post_init__(self) -> None:
        (
            self.camera,
            self.day_obs,
            self.group,
            self.filename,
            self.ext,
        ) = self.parse_key()

    def __hash__(self) -> int:
        return int(f"0x{self.hash}", 0)


class NightReportPayload(TypedDict):
    text: NotRequired[dict]
    plots: NotRequired[list[NightReport]]


class NightReportDataDict(TypedDict):
    date: date
    night_report: NightReportPayload


class EventJSONDict(TypedDict):
    date: date | None
    channel_events: dict[str, list[Event]]
    metadata: dict[str, str] | None


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
