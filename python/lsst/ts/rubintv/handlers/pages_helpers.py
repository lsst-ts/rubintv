from calendar import Calendar
from datetime import date
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import Request
from lsst.ts.rubintv.config import config, rubintv_logger

__all__ = ["month_names", "calendar_factory", "build_title", "to_dict"]
logger = rubintv_logger()


def month_names() -> list[str]:
    """Returns a list of month names as words.

    Returns
    -------
    List[str]
        A list of month names.
    """
    return [date(2000, m, 1).strftime("%B") for m in list(range(1, 13))]


def calendar_factory() -> Calendar:
    # first weekday 0 is Monday
    calendar = Calendar(firstweekday=0)
    return calendar


def build_title(*title_parts: str) -> str:
    title = "RubinTV"
    to_append = " - ".join(title_parts)
    if to_append:
        title += " - " + to_append
    return title


def to_dict(object: Any | None) -> dict | None:
    if object is None:
        return None
    return object.__dict__


async def get_admin(request: Request) -> dict | None:
    """Retrieve the admin user details based on the request headers and
    application state.


    Parameters
    ----------
    request : `Request`
        The request object containing headers and application state.

    Returns
    -------
    user: `dict` | `None`
        A dictionary containing user details if the user is in the list for
        having admin privileges. If the user not in the admin list for the
        current location, `None` is returned to indicate restricted access.

        If the user is not in the admin list but the location admin does not
        enforce access restrictions (i.e. open admin access), an empty
        dictionary is returned.
        This represents a generic, unnamed user who is allowed to view the
        page but has no identity and is not greeted by name.

        This distinction allows downstream code to handle three cases:
        - Admin user: full access, user info available in the dict.
        - Non-admin user: access denied, `None` returned.
        - Anonymous access allowed: limited access permitted, empty dict
        returned.
    """
    if config.site_location in ["local", "test", "gha"]:
        return {}

    base_url = str(request.base_url)
    api_url = urljoin(base_url, config.auth_api_url)
    username: str | None = None
    async with httpx.AsyncClient() as client:
        logger.info("Requesting user data", api_url=api_url)
        response = await client.get(api_url)
        user_data = response.json()
        logger.info("Received user data", user_data=user_data)
        username = user_data.get("username")
        if username is None:
            logger.warning("No username found in user data", user_data=user_data)
            return None

    admin_list = request.app.state.models.admin_list
    if username in admin_list or admin_list == ["*"]:
        return user_data

    return None
