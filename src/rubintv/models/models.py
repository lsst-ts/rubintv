import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dateutil.tz import gettz

from rubintv.models.models_helpers import string_int_to_date


@dataclass
class Channel:
    """A container for a category of images from a `Camera`.

    Parameters
    ----------
    name : `str`
        Name of the channel.
    prefix : `str`
        Lookup prefix for the GCS Bucket.
    slug : `str`
        Simplified version of the name, lowercase with no white-space and only
        ``-`` or ``_`` seperators.
    label : `str`
        Optional extra string for GUI buttons. If not given, the label is set
        the same as the name.
    service_dependency : `str`
        Name of the production service on which the production generator of
        this channel depends. e.g. ``"auxtel_monitor"`` is dependent on
        ``"auxtel_isr_runner"``. Used as a url slug (see slug above).
    """

    name: str
    prefix: str
    slug: str = ""
    label: str = ""
    service_dependency: str = ""

    def __post_init__(self) -> None:
        if self.label == "":
            self.label = self.name


@dataclass
class Camera:
    """A container for a single camera

    Parameters
    ----------
    name : `str`
        Name of the camera/image producer.
    online : `bool`
        To display the camera or not.
    slug : `str`
        Simplified version of the name, lowercase with no white-space and only
        ``-`` or ``_`` seperators.
    metadata_slug: `str`
        Optional slug used for locating shared metadata files in the bucket.
        If none is given, the slug above is used.
    logo : `str`
        Name (including extension) of the image file to display in the GUI
        button. Images are looked for in ``"/static/images/logos/"``.
    has_image_viewer : `bool`
        If ``True`` a column is drawn in the table for this camera with a link
        generated to point to an external image viewer for each monitor event.
    channels : `dict` [`str`, `Channel`]
        `Channel` objects belonging to this camera, keyed by name.
    per_day_channels : `dict` [`str`, `Channel`]
        `Channel` objects belonging to this camera, keyed by name. Per day
        channels are for categories of event that only occur once per
        observation date e.g. a movie of the night's images.
    night_report_prefix: `str`
        Used to form part of the bucket lookup for night reports. If left unset
        the camera is considered not to produce night reports.
    """

    name: str
    online: bool
    _slug: str = field(init=False, repr=False)
    metadata_slug: str = ""
    logo: str = ""
    has_image_viewer: bool = False
    channels: dict[str, Channel] = field(default_factory=dict)
    per_day_channels: dict[str, Channel] = field(default_factory=dict)
    night_report_prefix: str = ""

    @property
    def slug(self) -> str:
        return self._slug

    @slug.setter
    def slug(self, slug: str) -> None:
        self._slug = slug
        if not self.metadata_slug:
            self.metadata_slug = slug


@dataclass
class Location:
    """_summary_

    Parameters
    ----------
    name: `str`
    bucket: `str`
    services: `list` [`str`]
    slug: `str`
    logo: `str`
    camera_groups: `dict` [`str`, `list` [`str`]]
    """

    name: str
    bucket: str
    services: list[str]
    slug: str = ""
    logo: str = ""
    camera_groups: dict[str, list[str]] = field(default_factory=dict)

    def all_cameras(self) -> list[str]:
        all_cams: list[str] = []
        for cam_list in self.camera_groups.values():
            for cam in cam_list:
                all_cams.append(cam)
        return all_cams


@dataclass
class Event:
    url: str
    name: str = field(init=False)
    prefix: str = field(init=False)
    obs_date: date = field(init=False)
    seq: int = field(init=False)

    def parse_filename(self, delimiter: str = "_") -> tuple:
        regex = r"\/rubintv[_\w]+\/"
        cleaned_up_url = re.split(regex, self.url)[-1]
        prefix, name = cleaned_up_url.split(
            "/"
        )  # We know the name is the last part of the URL
        nList = name.split(delimiter)
        the_date = nList[2]
        year, month, day = map(int, the_date.split("-"))
        seq_str = nList[4][:-4]  # Strip extension
        if seq_str == "final":
            seq = 99999
        else:
            seq = int(seq_str)
        return (name, prefix, date(year, month, day), seq)

    def clean_date(self) -> str:
        return self.obs_date.strftime("%Y-%m-%d")

    def __post_init__(self) -> None:
        self.name, self.prefix, self.obs_date, self.seq = self.parse_filename()


@dataclass
class Night_Report_Event:
    url: str
    prefix: str
    timestamp: int
    blobname: str = ""
    slug: str = field(init=False)
    group: str = field(init=False)
    name: str = field(init=False)
    _obs_date: str = field(init=False)
    file_ext: str = field(init=False)

    @property
    def obs_date(self) -> date:
        return string_int_to_date(self._obs_date)

    def parse_filename(self) -> tuple:
        parts = self.url.split(self.prefix + "/")[-1]
        # use spread in case of extended names later on
        d, group, *names = parts.split("/")
        obs_date = d
        slug, file_ext = "".join(names).split(".")
        name = "".join(slug).replace("_", " ")
        return (slug, group, name, obs_date, file_ext)

    def __post_init__(self) -> None:
        (
            self.slug,
            self.group,
            self.name,
            self._obs_date,
            self.file_ext,
        ) = self.parse_filename()

    def dict(self) -> dict:
        _dict = self.__dict__.copy()
        return _dict


def get_current_day_obs() -> date:
    """Get the current day_obs - the observatory rolls the date over at UTC-12"""
    utc = gettz("UTC")
    nowUtc = datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs
