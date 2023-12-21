from datetime import date
from typing import Any, Iterable

import structlog

from rubintv.models.models import Camera, Channel, Event, NightReport

__all__ = [
    "find_first",
    "find_all",
    "string_int_to_date",
    "date_str_to_date",
    "objects_to_events",
    "objects_to_ngt_reports",
]


def find_first(a_list: list[Any], key: str, to_match: str) -> Any | None:
    result = None
    if iterator := _find_by_key_and_value(a_list, key, to_match):
        try:
            result = next(iter(iterator))
        except StopIteration:
            pass
    return result


def find_all(a_list: list[Any], key: str, to_match: str) -> list[Any] | None:
    result = None
    if iterator := _find_by_key_and_value(a_list, key, to_match):
        result = list(iterator)
    return result


def _find_by_key_and_value(
    a_list: list[Any], key: str, to_match: str
) -> Iterable[Any] | None:
    result = None
    if not a_list:
        return None
    try:
        result = (o for o in a_list if o.model_dump()[key] == to_match)
    except IndexError:
        pass
    return result


def date_str_to_date(date_string: str) -> date:
    y, m, d = date_string.split("-")
    return date(int(y), int(m), int(d))


def string_int_to_date(date_string: str) -> date:
    """Returns a date object from a given date string in the
    form ``"YYYYMMDD"``.

    Parameters
    ----------
    date_string : `str`
        A date string in the form ``"YYYYMMDD"``.

    Returns
    -------
    `date`
        A date.
    """
    d = date_string
    return date(int(d[0:4]), int(d[4:6]), int(d[6:8]))


async def objects_to_events(objects: list[dict]) -> list[Event]:
    """Asynchronously convert a list of dictionaries to a list of Event
    objects.

    This function attempts to create Event objects from the given dictionaries.
    If a dictionary does not match the expected structure of an Event, a
    ValueError is caught, logged, and the function continues to process the
    next dictionary.

    Parameters
    ----------
    objects : list[dict]
        A list of dictionaries, each representing the data for an Event object.

    Returns
    -------
    list[Event]
        A list of Event objects created from the provided dictionaries.
    """
    logger = structlog.get_logger(__name__)
    events = []
    for object in objects:
        try:
            event = Event(**object)
            events.append(event)
        except ValueError as e:
            logger.error(e)
    return events


async def objects_to_ngt_reports(objects: list[dict]) -> list[NightReport]:
    logger = structlog.get_logger(__name__)
    night_reports: list[NightReport] = []
    for object in objects:
        try:
            event = NightReport(**object)
            night_reports.append(event)
        except ValueError as e:
            logger.info(e)
    return night_reports


async def event_list_to_channel_keyed_dict(
    event_list: list[Event], channels: list[Channel]
) -> dict[str, list[Event]]:
    days_events_dict = {}
    for channel in channels:
        days_events_dict[channel.name] = [
            event for event in event_list if event.channel_name == channel.name
        ]
    return days_events_dict


def get_image_viewer_link(camera: Camera, day_obs: date, seq_num: int) -> str:
    """Returns the url for the camera's external image viewer for a given date
    and seq num.

    Used in the template.

    Parameters
    ----------
    camera : `Camera`
        The given camera.
    day_obs : `date`
        The given date.
    seq_num : `int`
        The given seq num.

    Returns
    -------
    url : `str`
        The url for the image viewer for a single image.
    """
    date_int_str = day_obs.isoformat().replace("-", "")
    url = camera.image_viewer_link.format(day_obs=date_int_str, seq_num=seq_num)
    return url


async def make_table_from_event_list(
    events: list[Event], channels: list[Channel]
) -> dict[int, dict[str, dict]]:
    d: dict[int, dict[str, dict]] = {}
    for chan in channels:
        chan_events = [e for e in events if e.channel_name == chan.name]
        if chan_events:
            for e in chan_events:
                if not isinstance(e.seq_num, int):
                    continue
                if e.seq_num in d:
                    d[e.seq_num].update({chan.name: e.__dict__})
                else:
                    d.update({e.seq_num: {chan.name: e.__dict__}})
    table = {k: v for k, v in sorted(d.items(), reverse=True)}
    return table
