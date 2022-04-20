from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple


@dataclass
class Camera:
    name: str
    slug: str
    online: bool


@dataclass
class Channel:
    name: str
    prefix: str
    simplename: str
    endpoint: str = field(init=False)

    def __post_init__(self) -> None:
        self.endpoint = self.simplename + "events"


@dataclass
class Event:
    url: str
    name: str = field(init=False)
    prefix: str = field(init=False)
    date: datetime = field(init=False)
    seq: int = field(init=False)
    chans: list = field(init=False)

    def parse_filename(self, delimiter: str = "_") -> Tuple:
        cleaned_up_url = self.url.split("rubintv_data/")[-1]
        prefix, name = cleaned_up_url.split(
            "/"
        )  # We know the name is the last part of the URL
        nList = name.split(delimiter)
        date = nList[2]
        seq = nList[4][:-4]  # Strip extension
        return (name, prefix, datetime.strptime(date, "%Y-%m-%d"), int(seq))

    def cleanDate(self) -> str:
        return self.date.strftime("%Y-%m-%d")

    def humanDate(self) -> str:
        return self.date.strftime("%a %Y/%m/%d")

    def __post_init__(self) -> None:
        self.name, self.prefix, self.date, self.seq = self.parse_filename()
        self.chans = []


cameras = {
    "auxtel": Camera(name="Auxtel", slug="auxtel", online=True),
    "comcam": Camera(name="Comcam", slug="comcam", online=False),
    "lsstcam": Camera(name="LSSTcam", slug="lsstcam", online=False),
    "allsky": Camera(name="All Sky", slug="allsky", online=False),
}

per_event_channels = {
    "monitor": Channel(
        name="Monitor", prefix="auxtel_monitor", simplename="monitor"
    ),
    "spec": Channel(
        name="Spectrum", prefix="summit_specexam", simplename="spec"
    ),
    "im": Channel(
        name="Image Analysis", prefix="summit_imexam", simplename="im"
    ),
    "mount": Channel(
        name="Mount", prefix="auxtel_mount_torques", simplename="mount"
    ),
}

per_night_channels = {
    "rollingbuffer": Channel(
        name="Rolling Buffer", prefix="rolling_buffer", simplename="rolling"
    ),
    "movie": Channel(
        name="Tonight's Movie", prefix="movie", simplename="movie"
    ),
}
