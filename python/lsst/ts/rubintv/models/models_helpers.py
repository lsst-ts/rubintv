import asyncio
from datetime import date
from typing import Any, AsyncGenerator, Iterable

from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import Camera, Channel, Event, NightReportData

__all__ = [
    "find_first",
    "find_all",
    "string_int_to_date",
    "date_str_to_date",
    "objects_to_events",
    "all_objects_to_events",
    "objects_to_ngt_report_data",
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


def process_batch(batch: list[dict]) -> list[Event]:
    """Convert a batch of event dicts to Event objects.

    Parameters
    ----------
    batch : list[dict]
        A batch list of event dicts.

    Returns
    -------
    list[Event]
        A batch list of `Event` objects.
    """
    logger = rubintv_logger()
    events = []
    for obj in batch:
        try:
            event = Event(**obj)
            events.append(event)
        except ValueError as e:
            logger.error(e)
    return events


async def all_objects_to_events(objects: list[dict]) -> list[Event]:
    events = []
    async for events_batch in objects_to_events(objects):
        events.extend(events_batch)
    return events


async def objects_to_events(
    objects: list[dict], batch_size: int = 1000
) -> AsyncGenerator[list[Event], None]:
    """Asynchronously convert a list of dictionaries to a list of Event
    objects in batches.

    Parameters
    ----------
    objects : list[dict]
        A list of dictionaries, each representing the data for an Event object.
    batch_size : int, optional
        The size of each batch to process asynchronously, by default 1000

    Yields
    ------
    list[Event]
        A batch of Event objects created from the provided dictionaries.
    """
    # Split objects into batches and process them asynchronously
    for i in range(0, len(objects), batch_size):
        batch = objects[i : i + batch_size]
        events = await asyncio.to_thread(process_batch, batch)
        yield events


async def objects_to_ngt_report_data(objects: list[dict]) -> list[NightReportData]:
    logger = rubintv_logger()
    night_reports: list[NightReportData] = []
    for object in objects:
        try:
            event = NightReportData(**object)
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


def dict_from_list_of_named_objects(a_list: list[Any]) -> dict[str, Any]:
    return {obj.name: obj for obj in a_list if hasattr(obj, "name")}
