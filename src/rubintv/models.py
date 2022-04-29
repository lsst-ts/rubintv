from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple


@dataclass
class Channel:
    name: str
    prefix: str
    simplename: str
    endpoint: str = field(init=False)

    def __post_init__(self) -> None:
        self.endpoint = self.simplename + "events"


@dataclass
class Camera:
    name: str
    slug: str
    online: bool
    has_historical: bool = False
    channels: dict[str, Channel] = field(default_factory=dict)
    per_day_channels: dict[str, Channel] = field(default_factory=dict)


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
        return (name, prefix, datetime.strptime(date, "%Y-%m-%d"), seq)

    def cleanDate(self) -> str:
        return self.date.strftime("%Y-%m-%d")

    def humanDate(self) -> str:
        return self.date.strftime("%a %Y/%m/%d")

    def __post_init__(self) -> None:
        self.name, self.prefix, self.date, self.seq = self.parse_filename()
        self.chans = []


cameras = {
    "auxtel": Camera(
        name="Auxtel", slug="auxtel", online=True, has_historical=True
    ),
    "comcam": Camera(
        name="Comcam", slug="comcam", online=True, has_historical=True
    ),
    "lsstcam": Camera(name="LSSTcam", slug="lsstcam", online=False),
    "allsky": Camera(name="All Sky", slug="allsky", online=True),
}

cameras["allsky"].channels = {
    "still": Channel(
        name="Current Still", prefix="all_sky_current", simplename="still"
    ),
    "movie": Channel(
        name="Current Movie", prefix="all_sky_movies", simplename="movie"
    ),
}

cameras["auxtel"].channels = {
    "monitor": Channel(
        name="Monitor", prefix="auxtel_monitor", simplename="monitor"
    ),
    "im": Channel(
        name="Image Analysis", prefix="summit_imexam", simplename="im"
    ),
    "spec": Channel(
        name="Spectrum", prefix="summit_specexam", simplename="spec"
    ),
    "mount": Channel(
        name="Mount", prefix="auxtel_mount_torques", simplename="mount"
    ),
}
cameras["auxtel"].per_day_channels = {
    "rollingbuffer": Channel(
        name="Rolling Buffer", prefix="rolling_buffer", simplename="rolling"
    ),
    "movie": Channel(
        name="Tonight's Movie", prefix="movie", simplename="movie"
    ),
}

cameras["comcam"].channels = {
    "monitor": Channel(
        name="Monitor", prefix="comcam_monitor", simplename="monitor"
    ),
    "im": Channel(
        name="Image Analysis", prefix="comcam_imexam", simplename="im"
    ),
    "spec": Channel(
        name="Spectrum", prefix="comcam_specexam", simplename="spec"
    ),
    "mount": Channel(
        name="Mount", prefix="comcam_mount_torques", simplename="mount"
    ),
}
