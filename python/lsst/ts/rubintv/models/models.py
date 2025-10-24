"""Models for rubintv."""

import asyncio
import dataclasses
import re
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, TypedDict

from lsst.ts.rubintv import __version__
from lsst.ts.rubintv.config import config, rubintv_logger
from pydantic import BaseModel, ConfigDict
from pydantic.dataclasses import dataclass

logger = rubintv_logger()


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
    icon: str = ""
    text_colour: str = "#000"


class HasButton(BaseModel):
    """Base class for classes that are displayed on-screen with buttons.
    Provides a name, title, logo image, text colour and whether the text
    should have a drop-shadow.

    Attributes
    ----------
    name : str
        The name of the entity.
    title : str
        The title associated with the entity.
    logo : str
        The logo associated with the entity. Defaults to an empty string,
        which is no logo.
    text_colour : str
        The hex value of a CSS colour.
    text_shadow : bool
        True for a shadow, false otherwise.
    """

    title: str
    name: str = ""
    logo: str = ""
    text_colour: str = "#000"
    text_shadow: bool = False


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MosaicViewMeta(BaseModel):
    """Populated in the models data YAML file, each MosaicViewMeta object pairs
    a channel name with a set of metadata columns to display alongside the
    current image for that channel.

    Attributes
    ----------
    channel : str
        The channel name.
    metaColumns : list[str]
        A list of metadata columns.
    dataType : MediaType
        Presently, IMAGE or VIDEO are the only options.
    """

    channel: str
    metaColumns: list[str]
    mediaType: MediaType = MediaType.IMAGE


class ExtraButton(HasButton):
    """Sub-class to provide buttons with the functionality to link to relative
    URLs.

    Attributes
    ----------
    linkURL: str
        A relative URL. e.g "mosaic" on
        https://usdf-rsp-dev.slac.stanford.edu/rubintv/summit-usdf/comcam
        will point to
        https://usdf-rsp-dev.slac.stanford.edu/rubintv/summit-usdf/comcam/mosaic
    """

    linkURL: str


class TimeSinceClock(BaseModel):
    """The presence of a `TimeSinceClock` in a `Camera` means that the both the
    table view and individual channels views for that camera will display a
    clock that shows the time since the last image was taken. This data is
    derived from the most recent seq_num from the table.

    Attributes
    ----------
    label: str
        The label that appears before the time part of the clock.

    """

    label: str


class Camera(HasButton):
    """Represents a camera entity, capable of handling different channels like
    images or movies.

    This class extends the Pydantic BaseModel to leverage data validation. It
    includes various attributes related to the camera, like its name, online
    status, and associated channels. It also provides methods for setting
    default values and categorizing channels.

    Attributes
    ----------
    online : bool
        Indicates whether the camera is online.
    metadata_from : str, optional
        The source of metadata for the camera. Defaults to an empty string and
        uses `name` if not set.
    channels : list[Channel]
        A list of channels (either images or movies) associated with the
        camera. Defaults to an empty list.
    night_report_label : str, optional
        Label for the night report. Defaults to "Night's Evolution".
    metadata_cols : dict[str, str] | None, optional
        A dictionary defining metadata columns. Defaults to
        None.
    image_viewer_link : str, optional
        A link to the image viewer. Defaults to an empty string.
    copy_row_template : str, optional
        Template string for copying a row. Defaults to an empty string.
    mosaic_view_meta : list[MosaicViewMeta], optional
        List of channels and associated metadata columns for a mosaic view of
        current images and plots.
    extra_buttons : list[ExtraButton], optional
        Any extra buttons to link to other parts of the website.
    time_since_clock : TimeSinceClock
        Label to display next to the time since (for e.g. last image) clock.


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
    night_report_label: str = "Night's Evolution"
    metadata_columns: dict[str, str] | None = None
    image_viewer_link: str = ""
    copy_row_template: str = ""
    mosaic_view_meta: list[MosaicViewMeta] = []
    extra_buttons: list[ExtraButton] = []
    time_since_clock: TimeSinceClock | None = None

    def seq_channels(self) -> list[Channel]:
        return [c for c in self.channels if not c.per_day]

    def pd_channels(self) -> list[Channel]:
        return [c for c in self.channels if c.per_day]


class Location(HasButton):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    bucket_name: str
    profile_name: str
    endpoint_url: str | None = None
    camera_groups: dict[str, list[str]]
    cameras: list[Camera] = []
    services: list[str] = []
    is_teststand: bool = False
    has_cluster_status: bool = False


@dataclass
class Event:
    key: str
    # derived fields:
    camera_name: str = ""
    day_obs: str = ""
    channel_name: str = ""
    seq_num: int | str = ""
    filename: str = ""
    ext: str = ""

    def __lt__(self, other: Any) -> bool:
        """Used by max()"""
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
class NightReportData:
    """Wrapper for a night report file metadata object.

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
    camera_name: `str`
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
    camera_name: str = ""
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
            camera_name, day_obs_str, filename, ext = parts
            group = "metadata"
        else:
            plot_re = re.compile(
                r"(\w+)\/([\d-]+)\/night_report\/([\w-]+)\/([\w-]+)\.(\w+)$"
            )
            if match := plot_re.match(key):
                parts = match.groups()
                camera_name, day_obs_str, group, filename, ext = parts
                filename = filename + "." + ext
            else:
                raise ValueError(f"Key can't be parsed: {key}")

        return (camera_name, day_obs_str, group, filename, ext)

    def __post_init__(self) -> None:
        (
            self.camera_name,
            self.day_obs,
            self.group,
            self.filename,
            self.ext,
        ) = self.parse_key()

    def __hash__(self) -> int:
        if not re.match(r"^[0-9a-fA-F]+$", self.hash):
            raise ValueError(f"Hash is not a valid hex value: {self.hash}")
        return int(f"0x{self.hash}", 0)


class NightReport(BaseModel):
    text: dict[str, Any] | None = {}
    plots: list[NightReportData] | None = []


def get_current_day_obs() -> date:
    """Get the current day_obs.

    The observatory rolls the date over at UTC minus 12 hours.

    Returns
    -------
    dayObs : `date`
        The current observation day.
    """
    nowUtc = datetime.now(timezone.utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs


class Heartbeat:
    class Status(Enum):
        STOPPED = 0
        ACTIVE = 1

    def __init__(self, service_name: str, next_expected: datetime) -> None:
        self.service_name = service_name
        self.state = Heartbeat.Status.ACTIVE
        self.next_expected = next_expected
        self.task = asyncio.create_task(self.monitor_heartbeat())

    async def monitor_heartbeat(self) -> None:
        """Continuously monitors the heartbeat and updates the service
        state."""
        while True:
            nowUtc = datetime.now(timezone.utc)
            wait_seconds = (self.next_expected - nowUtc).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            else:
                self.state = Heartbeat.Status.STOPPED
                logger.warn("Service has gone down:", service=self.service_name)
                break  # Exit the loop if service is down

    def update_heartbeat(self, next_expected: datetime) -> None:
        """Updates the heartbeat's next expected time and resets state to
        running."""
        self.next_expected = next_expected
        if self.state == Heartbeat.Status.STOPPED:
            self.state = Heartbeat.Status.ACTIVE
            # If the service was down, restart the monitoring task
            self.task = asyncio.create_task(self.monitor_heartbeat())
            logger.info("Service is back:", service=self.service_name)

    def to_json(self) -> dict[str, str | bool]:
        return {
            "serviceName": self.service_name,
            "isActive": bool(self.state.value),
            "nextExpected": self.next_expected.isoformat(),
        }


class ServiceTypes(str, Enum):
    """The types of services provided by RubinTV."""

    CAMERA = "camera"
    CHANNEL = "channel"
    NIGHTREPORT = "nightreport"
    HISTORICALSTATUS = "historicalStatus"
    CALENDAR = "calendar"
    DETECTORS = "detectors"


class ServiceMessageTypes(Enum):
    CHANNEL_EVENT = "event"
    LATEST_EVENT = "latestEvent"
    CAMERA_TABLE = "channelData"
    CAMERA_METADATA = "metadata"
    LATEST_METADATA = "latestMetadata"
    CAMERA_PER_DAY = "perDay"
    CAMERA_PD_BACKDATED = "perDayBackdated"
    NIGHT_REPORT = "nightReport"
    HISTORICAL_STATUS = "historicalStatus"
    DAY_CHANGE = "dayChange"
    PREV_NEXT = "prevNext"
    ALL_CHANNELS = "allChannels"
    DETECTOR_STATUS = "detectorStatus"


class KeyValue(BaseModel):
    """A simple key-value pair."""

    key: str
    value: str | int | float | bool | None = None


type StructuredData = dict[str, dict[str, dict[str, set[int | str]]]]


class ExtensionDict(TypedDict):
    default: str
    exceptions: dict[int | str, str]


type ExtensionInfo = dict[str, ExtensionDict]
type ChannelData = dict[int, dict[str, dict]]


@dataclass
class CameraPageData:
    """Data for a camera page."""

    per_day: dict[str, dict] = dataclasses.field(default_factory=dict)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    metadata_exists: bool = False
    nr_exists: bool = False

    def is_empty(self) -> bool:
        """Check if the data is empty."""
        return not any(
            [
                self.metadata_exists or self.metadata,
                self.per_day,
                self.nr_exists,
            ]
        )


@dataclass
class HistoricalPageData(CameraPageData):
    """Data for the historical page."""

    structured_data: dict[str, set[int | str]] = dataclasses.field(default_factory=dict)
    extension_info: ExtensionInfo = dataclasses.field(default_factory=dict)

    def is_empty(self) -> bool:
        """Check if the data is empty."""
        base_empty = super().is_empty()
        return base_empty and not any(
            [
                self.structured_data,
                self.extension_info,
            ]
        )


@dataclass
class CurrentPageData(CameraPageData):
    """Data for the current page."""

    channel_data: ChannelData = dataclasses.field(default_factory=dict)

    def is_empty(self) -> bool:
        """Check if the data is empty."""
        base_empty = super().is_empty()
        return base_empty and not self.channel_data
