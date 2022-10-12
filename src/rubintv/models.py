from dataclasses import dataclass, field
from datetime import datetime
from typing import Tuple


@dataclass
class Channel:
    name: str
    prefix: str
    simplename: str
    label: str = ""
    endpoint: str = field(init=False)
    service_dependency: str = ""

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
        seq_str = nList[4][:-4]  # Strip extension
        if seq_str == "final":
            seq = 99999
        else:
            seq = int(seq_str)
        return (name, prefix, datetime.strptime(date, "%Y-%m-%d"), seq)

    def clean_date(self) -> str:
        return self.date.strftime("%Y-%m-%d")

    def __post_init__(self) -> None:
        self.name, self.prefix, self.date, self.seq = self.parse_filename()
        self.chans = []


cameras = {
    "auxtel": Camera(
        name="AuxTel", slug="auxtel", online=True, has_historical=True
    ),
    "comcam": Camera(
        name="ComCam", slug="comcam", online=True, has_historical=True
    ),
    "lsstcam": Camera(name="LSSTCam", slug="lsstcam", online=False),
    "allsky": Camera(
        name="All Sky", slug="allsky", online=True, has_historical=True
    ),
}

cameras["allsky"].channels = {
    "image": Channel(
        name="Current Image", prefix="all_sky_current", simplename="image"
    ),
    "monitor": Channel(
        name="Current Movie", prefix="all_sky_movies", simplename="movie"
    ),
}

cameras["auxtel"].channels = {
    "monitor": Channel(
        name="Monitor",
        prefix="auxtel_monitor",
        simplename="monitor",
        label="Monitor",
        service_dependency="auxtel_isr_runner",
    ),
    "im": Channel(
        name="Image Analysis",
        prefix="summit_imexam",
        simplename="im",
        label="ImAnalysis",
        service_dependency="auxtel_isr_runner",
    ),
    "spec": Channel(
        name="Spectrum",
        prefix="summit_specexam",
        simplename="spec",
        label="Spectrum",
        service_dependency="auxtel_isr_runner",
    ),
    "mount": Channel(
        name="Mount",
        prefix="auxtel_mount_torques",
        simplename="mount",
        label="Mount",
    ),
}
cameras["auxtel"].per_day_channels = {
    "rollingbuffer": Channel(
        name="Rolling Buffer",
        prefix="auxtel_rolling_buffer",
        simplename="rolling",
        label="Rolling GIF for ",
    ),
    "movie": Channel(
        name="Tonight's Movie",
        prefix="auxtel_movies",
        simplename="movie",
        label="Movie for ",
    ),
}

cameras["comcam"].channels = {
    "monitor": Channel(
        name="Central CCD Monitor",
        prefix="comcam_monitor",
        simplename="monitor",
        label="Monitor",
    ),
}

production_services = {
    "auxtel": {
        "display_name": "AuxTel",
        "channels": cameras["auxtel"].channels,
        "services": {
            "auxtel_metadata": "Metadata",
            "auxtel_isr_runner": "ISR Runner",
        },
    },
    "allsky": {
        "display_name": "All Sky",
        "services": {
            "allsky": "All Sky",
        },
    },
    "comcam": {
        "display_name": "ComCam",
        "channels": cameras["comcam"].channels,
    },
    "misc": {
        "display_name": "Misc Services",
        "services": {
            "backgroundService": "Background",
        },
    },
}
