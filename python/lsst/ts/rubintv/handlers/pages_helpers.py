from calendar import Calendar
from datetime import date
from typing import Any

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
        A dictionary containing user details if the user is an admin,
        otherwise `None`. An empty dictionary is returned if the user
        is anonymous (i.e., they are not a named user but have access
        to the admin page, as this location has no admin restrictions).
    """
    if config.site_location in ["local", "test"]:
        return {}

    username = request.headers.get("X-Auth-Request-User")
    email = request.headers.get("X-Auth-Request-Email")
    admin_list = request.app.state.models.admin_list

    if username in admin_list or admin_list == ["*"]:
        logger.info("Admin page accessed", username=username, email=email)
        users_names = request.app.state.models.users_names
        if username in users_names:
            name = users_names[username]
            return {"name": name, "username": username, "email": email}
        else:
            return {}
    return None
