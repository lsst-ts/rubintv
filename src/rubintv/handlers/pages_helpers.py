from calendar import Calendar
from datetime import date

import structlog

from rubintv.models.models import Channel, Event

__all__ = ["make_table_rows_from_columns_by_seq", "build_title"]


def make_table_rows_from_columns_by_seq(
    event_data: dict, channels: list[Channel]
) -> dict[int, dict[str, Event]]:
    """Returns a dict of dicts of `Events`, keyed outwardly by sequence number
    and inwardly by channel name for displaying as a table.

    If a sequence number appears in the given metadata that is not otherwise
    in the given `events_dict` it is appended as the key for an empty dict.
    This is so that if metadata exists, a row can be drawn on the table without
    there needing to be anything in the channels.

    Parameters
    ----------
    ch_events : `dict` [`str`, `list` [`Event`] | None]
        The events to sort, keyed by channel name.

    metadata : `dict` [`str`, `dict` [`str`, `str`]]
        A dictionary of metadata outer keyed by sequence number and the inner
        by table column name.

    channels: `list` [`Channel`]
        A list of channels to sort the events by.

    Returns
    -------
    rows_dict : `dict` [`int`, `dict` [`str`, `Event`]]
        A dict that represents a table of `Event`s, keyed by ``seq`` and with
        an inner dict with an entry for each `Channel` for that seq num.

    """
    logger = structlog.get_logger(__name__)
    d: dict[int, dict[str, Event]] = {}
    if dict_events := event_data["channel_events"]:
        for chan in channels:
            chan_events = dict_events[chan.name]
            if chan_events:
                for e in chan_events:
                    if not isinstance(e.seq_num, int):
                        continue
                    if e.seq_num in d:
                        d[e.seq_num].update({chan.name: e})
                    else:
                        d.update({e.seq_num: {chan.name: e}})
    # add an empty row for sequence numbers found only in metadata
    if metadata := event_data["metadata"]:
        for seq_str in metadata:
            try:
                seq = int(seq_str)
                if seq not in d:
                    d[seq] = {}
            except ValueError:
                logger.warn("Warning: Non-integer seq num ignored")
    # d == {seq: {chan1: event, chan2: event, ... }}
    # make sure the table is in order
    rows_dict = {k: v for k, v in sorted(d.items(), reverse=True)}
    return rows_dict


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


def build_title() -> None:
    return
