"""Models for rubintv."""

import asyncio
import re
from datetime import date, datetime, timedelta
from typing import Any

import structlog
from dateutil.tz import gettz
from pydantic import BaseModel, ConfigDict, validator
from pydantic.dataclasses import dataclass
from typing_extensions import NotRequired, TypedDict

from .. import __version__
from ..config import config

__all__ = [
    "Metadata",
    "Location",
    "Channel",
    "Camera",
    "Event",
    "get_current_day_obs",
]

logger = structlog.get_logger("rubintv")


class Metadata(BaseModel):
    """Metadata about the application."""

    name: str = config.name
    """The name of the application."""

    version: str = __version__
    """The version of the application."""

    description: str = "rubinTV is a Web app to display Butler-served data sets"
    """A description of the application."""

    repository_url: str = "https://github.com/lsst-ts/rubintv'"
    """The URL of the application's repository."""

    documentation_url: str = "https://rubintv.lsst.io"
    """The URL of the application's documentation."""


class Channel(BaseModel):
    name: str
    title: str
    label: str = ""
    per_day: bool = False
    colour: str = ""


class HasButton(BaseModel):
    name: str
    title: str
    logo: str = ""
    text_colour: str = "#000"
    text_shadow: str = ""


class Camera(HasButton):
    """Represents a camera entity, capable of handling different channels like
    images or movies.

    This class extends the Pydantic BaseModel to leverage data validation. It
    includes various attributes related to the camera, like its name, online
    status, and associated channels. It also provides methods for setting
    default values and categorizing channels.

    Attributes
    ----------
    name : str
        The name of the camera.
    title : str
        The title associated with the camera.
    online : bool
        Indicates whether the camera is online.
    metadata_from : str, optional
        The source of metadata for the camera. Defaults to an empty string and
        uses `name` if not set.
    logo : str, optional
        The logo associated with the camera. Defaults to an empty string.
    channels : list[Channel]
        A list of channels (either images or movies) associated with the
        camera. Defaults to an empty list.
    night_report_label : str, optional
        Label for the night report. Defaults to "Night Report".
    metadata_cols : dict[str, str] | None, optional
        A dictionary defining metadata columns. Defaults to
        None.
    image_viewer_link : str, optional
        A link to the image viewer. Defaults to an empty string.
    copy_row_template : str, optional
        Template string for copying a row. Defaults to an empty string.

    Methods
    -------
    default_as_name(cls: Type, v: str, values: Any) -> str
        A class method that acts as a field validator for 'metadata_from'. It
        defaults to using `name` if `metadata_from` is not set.
    seq_channels() -> list[Channel]
        Returns a list of sequential channels, i.e., channels that do not have
        a per-day configuration.
    pd_channels() -> list[Channel]
        Returns a list of per-day channels, i.e., channels that have a per-day
        configuration.
    """
    online: bool
    metadata_from: str = ""
    channels: list[Channel] = []
    night_report_label: str = "Night Report"
    metadata_cols: dict[str, str] | None = None
    image_viewer_link: str = ""
    copy_row_template: str = ""

    @validator("metadata_from", pre=True, always=True)
    def default_metadata_from(cls: Any, v: Any, values: Any) -> Any:
        return v or values.get("name", "")

    def seq_channels(self) -> list[Channel]:
        return [c for c in self.channels if not c.per_day]

    def pd_channels(self) -> list[Channel]:
        return [c for c in self.channels if c.per_day]


class Location(HasButton):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    bucket_name: str
    profile_name: str
    camera_groups: dict[str, list[str]]
    cameras: list[Camera] = []
    services: list[str] = []


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

    def __lt__(self, other: Any) -> bool:
        if type(other) is not type(self):
            raise TypeError
        return self.key < other.key

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
        name_re = re.compile(r"(\w+)\/([\d-]+)\/(\w+)\/(\d{6}|final)\/([\w-]+)\.(\w+)$")
        if match := name_re.match(key):
            parts = match.groups()
        else:
            raise ValueError(f"Key can't be parsed: {key}")

        camera, day_obs_str, channel, seq_num, filename, ext = parts
        filename = filename + "." + ext

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
        return self.seq_num if isinstance(self.seq_num, int) else 99999


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
        metadata_re = re.compile(r"(\w+)\/([\d-]+)\/night_report\/([\w-]+md)\.(\w+)$")
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
                filename = filename + "." + ext
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


class Heartbeat:
    def __init__(self, service_name: str, next_expected: datetime) -> None:
        self.service_name = service_name
        self.state = "running"
        self.next_expected = next_expected
        self.task = asyncio.create_task(self.monitor_heartbeat())

    async def monitor_heartbeat(self) -> None:
        """Continuously monitors the heartbeat and updates the service
        state."""
        while True:
            now = datetime.utcnow()
            wait_seconds = (self.next_expected - now).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            else:
                self.state = "stopped"
                logger.warn("Service has gone down:", service=self.service_name)
                break  # Exit the loop if service is down

    def update_heartbeat(self, next_expected: datetime) -> None:
        """Updates the heartbeat's next expected time and resets state to
        running."""
        self.next_expected = next_expected
        if self.state == "stopped":
            self.state = "running"
            # If the service was down, restart the monitoring task
            self.task = asyncio.create_task(self.monitor_heartbeat())
            logger.info("Service is back:", service=self.service_name)

    def to_json(self) -> dict[str, str]:
        return {
            "service_name": self.service_name,
            "state": self.state,
            "next_expected": self.next_expected.isoformat(),  # Convert datetime to string
        }
