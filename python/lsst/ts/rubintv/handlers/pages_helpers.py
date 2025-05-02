from typing import Any

from fastapi import Request

__all__ = ["build_title", "to_dict", "get_admin"]


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

        If the location does not enforce access restrictions (i.e. open
        admin access), an empty dictionary is returned.
        This represents a generic, unnamed user who is allowed to
        view the page, but has no identity and won't be greeted by name.

        This distinction allows downstream code to handle three cases:
        - Admin user: full access, user info available in the dict.
        - Non-admin user: access denied, `None` returned.
        - Anonymous access allowed: limited access permitted, empty dict
        returned.
    """
    admin_list = request.app.state.models.admin_list
    if admin_list == ["*"]:
        return {}

    username = request.headers.get("X-Auth-Request-User")
    email = request.headers.get("X-Auth-Request-Email")
    if username in admin_list:
        return {"username": username, "email": email}

    return None
