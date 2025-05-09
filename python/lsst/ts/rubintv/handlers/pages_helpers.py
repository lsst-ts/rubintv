from typing import Any

from fastapi import Request

from ..config import rubintv_logger

logger = rubintv_logger()

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


async def get_key_from_type_and_visit(
    camera_name: str,
    type: str,
    visit: str,
) -> str:
    """Get the key from the type and visit.
    e.g from type="calexp_mosaic" and visit="2025042200233" return
    key="lsstcam/2025-04-22/calexp_mosaic/000233/lsstcam_calexp_mosaic_2025-04-22_000233.jpg"
    key="lsstcam/2025-04-22/calexp_mosaic/000233/lsstcam_calexp_mosaic_2025-04-22_000233
    """
    try:
        day_obs_no_hyphens = visit[:8]
        day_obs = f"{day_obs_no_hyphens[:4]}-{day_obs_no_hyphens[4:6]}-{day_obs_no_hyphens[6:]}"
        seq_num = f"{int(visit[8:]):06}"
        key = f"{camera_name}/{day_obs}/{type}/{seq_num}/{camera_name}_{type}_{day_obs}_{seq_num}"
    except ValueError:
        logger.error(f"Invalid visit number: {visit}. Expected format: YYYYMMDDHHMMSS.")
        key = ""
    logger.debug(f"Key generated: {key}")
    return key
