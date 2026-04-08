from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import Event

logger = rubintv_logger(__name__)


def get_next_prev_seq_nums(
    seq_nums: set[int] | list[int], current_seq_num: int
) -> tuple[int | None, int | None]:
    """Find next and previous seq_nums from a set/list of seq_nums.

    Parameters
    ----------
    seq_nums : set[int] | list[int]
        Collection of available seq_nums (will be sorted).
    current_seq_num : int
        The current seq_num to find next/prev for.

    Returns
    -------
    next_seq : int | None
        The next seq_num, or None if at end.
    prev_seq : int | None
        The previous seq_num, or None if at start.
    """
    if not seq_nums or current_seq_num not in seq_nums:
        return (None, None)

    # Sort and find position
    sorted_seqs = sorted(seq_nums)
    idx = sorted_seqs.index(current_seq_num)

    next_seq = sorted_seqs[idx + 1] if idx + 1 < len(sorted_seqs) else None
    prev_seq = sorted_seqs[idx - 1] if idx > 0 else None

    return (next_seq, prev_seq)


async def get_next_previous_from_table(
    table: dict[int, dict[str, dict]], event: Event | dict
) -> tuple[dict | None, dict | None]:
    """Takes an Event and a table of Event dicts keyed by seq. num and channel
    name and returns the next and previous event dicts.

    Parameters
    ----------
    table : dict[int, dict[str, dict]]
        The table of Event dicts keyed by seq_num, then channel_name.
    event : Event | dict
        The given event to find previous/next events to.

    Returns
    -------
    nxt_prv: tuple[dict | None, dict | None]
        A tuple of (next_dict, prev_dict) or (None, None) if not found.
    """
    chan = event["channel_name"] if isinstance(event, dict) else event.channel_name
    seq_num = event["seq_num"] if isinstance(event, dict) else event.seq_num

    # this should never happen
    if isinstance(seq_num, str):
        logger.warning("Looking for prev/next for Per Day Event")
        return (None, None)

    # Get seq_nums that have this channel
    chan_seq_nums = [seq for seq, channels in table.items() if chan in channels]

    # Use helper to find next/prev seq_nums
    next_seq, prev_seq = get_next_prev_seq_nums(chan_seq_nums, seq_num)

    nxt_dict = table.get(next_seq, {}).get(chan) if next_seq else None  # type: ignore
    prv_dict = table.get(prev_seq, {}).get(chan) if prev_seq else None  # type: ignore

    return (nxt_dict, prv_dict)
