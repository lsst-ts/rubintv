from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dateutil.tz import gettz


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


cameras = {
    "auxtel": Camera(
        name="AuxTel", slug="auxtel", online=True, has_historical=True
    ),
    "startracker": Camera(
        name="StarTracker", slug="startracker", online=False
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
    "movie": Channel(
        name="Current Movie", prefix="all_sky_movies", simplename="movie"
    ),
    "image": Channel(
        name="Current Image", prefix="all_sky_current", simplename="image"
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

cameras["startracker"].channels = {
    "monitor": Channel(
        name="StarTracker",
        prefix="startracker",
        simplename="startracker",
        label="StarTracker",
    ),
    "analysis": Channel(
        name="StarTracker Analysis",
        prefix="startracker_analysis",
        simplename="analysis",
        label="Analysis",
    ),
    "wide": Channel(
        name="StarTracker Wide",
        prefix="startracker_wide",
        simplename="wide",
        label="Wide",
    ),
    "wide_analysis": Channel(
        name="StarTracker Analysis",
        prefix="startracker_wide_analysis",
        simplename="wide_analysis",
        label="Wide Analysis",
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
    "startracker": {
        "display_name": "StarTracker",
        "channels": cameras["startracker"].channels,
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


def get_current_day_obs() -> date:
    """Get the current day_obs - the observatory rolls the date over at UTC-12"""
    utc = gettz("UTC")
    nowUtc = datetime.now().astimezone(utc)
    offset = timedelta(hours=-12)
    dayObs = (nowUtc + offset).date()
    return dayObs
