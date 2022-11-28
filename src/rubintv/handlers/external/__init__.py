"""Externally-accessible endpoint handlers that serve relative to
``/<app-name>/``.
"""

__all__ = [
    "get_page",
    "get_admin_page",
    "reload_historical",
    "request_heartbeat_for_channel",
    "request_all_heartbeats",
    "get_all_sky_current",
    "get_all_sky_current_update",
    "get_allsky_historical",
    "get_allsky_historical_movie",
    "get_recent_table",
    "update_todays_table",
    "get_historical",
    "get_historical_day_data",
    "events",
    "current",
]

from rubintv.handlers.external.endpoints import (
    current,
    events,
    get_recent_table,
)
