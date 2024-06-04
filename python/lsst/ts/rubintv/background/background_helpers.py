import structlog
from lsst.ts.rubintv.models.models import Event

logger = structlog.get_logger("rubintv")


async def get_next_previous_from_table(
    table: dict[int, dict[str, dict]], event: Event
) -> tuple[dict | None, ...]:
    """Takes an Event and a table of Event dicts keyed by seq. num and channel
    name and returns the next and previous event dicts.

    Parameters
    ----------
    table : dict[int, dict[str, dict]]
        The table of Event dicts.
    event : Event
        The given event to find previous/next events to.

    Returns
    -------
    nxt_prv: tuple[dict | None, ...]
        A tuple of two elements containing the next and previous events to the
        given event, or None in either place if there is no such event.
    """
    chan = event.channel_name
    chan_table = {}

    # reduces table to event's channel single
    for seq, channels in table.items():
        if chan in channels:
            chan_table[seq] = table[seq][chan]
    if chan_table == {}:
        return (None, None)

    # creates a 'None' padded list of seq. nums
    padded_seqs = [None, *chan_table.keys(), None]

    # find the index of event's seq num in that padded list
    index = padded_seqs.index(event.seq_num_force_int())

    next_seq = padded_seqs[index - 1]
    prev_seq = padded_seqs[index + 1]

    nxt_prv = (
        chan_table.get(next_seq),  # type: ignore
        chan_table.get(prev_seq),  # type: ignore
    )

    return nxt_prv
