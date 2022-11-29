from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dateutil.tz import gettz


@dataclass
class Channel:
    name: str
    prefix: str
    simplename: str = ""
    label: str = ""
    service_dependency: str = ""

    def __post_init__(self) -> None:
        if self.label == "":
            self.label = self.name

    @property
    def endpoint(self) -> str:
        return self.simplename + "events"


@dataclass
class Camera:
    name: str
    online: bool
    _slug: str = field(init=False, repr=False)
    metadata_slug: str = ""
    has_image_viewer: bool = False
    channels: dict[str, Channel] = field(default_factory=dict)
    per_day_channels: dict[str, Channel] = field(default_factory=dict)

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
    name: str
    bucket: str
    services: list[str]
    slug: str = ""
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
        cleaned_up_url = self.url.split("rubintv_data/")[-1]
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


def get_current_day_obs() -> date:
    """Get the current day_obs - the observatory rolls the date over at UTC-12"""
    utc = gettz("UTC")
    nowUtc = datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs
