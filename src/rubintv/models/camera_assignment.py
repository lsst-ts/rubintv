from .models import Camera, Channel

cameras = {
    "auxtel": Camera(
        name="AuxTel",
        slug="auxtel",
        online=True,
        has_historical=True,
        has_image_viewer=True,
    ),
    "startracker": Camera(
        name="StarTracker",
        slug="startracker",
        online=True,
        has_historical=True,
    ),
    "startracker-wide": Camera(
        name="StarTracker Wide",
        slug="startracker-wide",
        online="true",
        has_historical=True,
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
    "startracker": Channel(
        name="StarTracker",
        prefix="startracker_raw",
        simplename="startracker",
        label="StarTracker",
    ),
    "analysis": Channel(
        name="StarTracker Analysis",
        prefix="startracker_analysis",
        simplename="analysis",
        label="Analysis",
    ),
}

cameras["startracker-wide"].channels = {
    "startracker-wide": Channel(
        name="StarTracker Wide",
        prefix="startracker_wide_raw",
        simplename="startracker-wide",
        label="ST Wide",
    ),
    "startracker-wide-analysis": Channel(
        name="StarTracker Wide Analysis",
        prefix="startracker_wide_analysis",
        simplename="startracker-wide-analysis",
        label="ST Wide Analysis",
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
        "services": {
            "startracker_metadata": "Metadata",
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
