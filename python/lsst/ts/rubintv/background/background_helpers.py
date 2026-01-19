from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.models.models import Event, ExtensionInfo, StructuredData

logger = rubintv_logger()


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

    # this should never happen
    if isinstance(event.seq_num, str):
        logger.warning("Looking for prev/next for Per Day Event")
        return (None, None)

    # creates a 'None' padded list of seq. nums
    all_seqs = sorted(set(chan_table.keys() | {event.seq_num}))
    padded_seqs = [None, *all_seqs, None]

    # find the index of event's seq num in that padded list
    index = padded_seqs.index(event.seq_num)

    next_seq = padded_seqs[index + 1]
    prev_seq = padded_seqs[index - 1]

    nxt_prv = (
        chan_table.get(next_seq),  # type: ignore
        chan_table.get(prev_seq),  # type: ignore
    )

    return nxt_prv


async def make_structured_data(
    events: list[Event],
) -> StructuredData:
    """Build structured data from events.

    Structure: {channel_name: {seq_num1, seq_num2, ...}}

    This is a compressed format suitable for WebSocket transmission.

    Parameters
    ----------
    events : list[Event]
        List of events to build structured data from.

    Returns
    -------
    structured: StructuredData
        Structured data mapping channel names to sets of sequence numbers.
    """
    structured: StructuredData = {}
    for event in events:
        channel_name = event.channel_name
        seq_num = event.seq_num
        if channel_name not in structured:
            structured[channel_name] = set()
        structured[channel_name].add(seq_num)
    return structured


async def make_extension_info(
    events: list[Event],
) -> ExtensionInfo:
    """Build extension info from events.

    Structure:
        {channel_name: {"default": "ext", "exceptions": {seq_num: "ext"}}}

    This is needed for the frontend to reconstruct filenames from
    structuredData.

    Parameters
    ----------
    events : list[Event]
        List of events to build extension info from.

    Returns
    -------
    extension_info: ExtensionInfo
        Extension info mapping channel names to extension metadata.
        Each channel has a default extension and exceptions for specific
        seq_nums.
    """
    extension_info: ExtensionInfo = {}
    extension_counts: dict[str, dict[str, int]] = {}

    for event in events:
        channel_name = event.channel_name
        ext = event.ext
        if channel_name not in extension_info:
            extension_info[channel_name] = {"default": "jpg", "exceptions": {}}
            extension_counts[channel_name] = {}

        # Track extension frequency to determine default
        if ext not in extension_counts[channel_name]:
            extension_counts[channel_name][ext] = 0
        extension_counts[channel_name][ext] += 1

    # Set default to most common extension, record others as exceptions
    for channel_name, ext_counts in extension_counts.items():
        if ext_counts:
            default_ext = max(ext_counts.items(), key=lambda x: x[1])[0]
            extension_info[channel_name]["default"] = default_ext

    # Mark extensions different from default as exceptions
    for event in events:
        channel_name = event.channel_name
        ext = event.ext
        default_ext = extension_info[channel_name]["default"]
        if ext != default_ext:
            seq_num = (
                int(event.seq_num) if isinstance(event.seq_num, str) else event.seq_num
            )
            extension_info[channel_name]["exceptions"][seq_num] = ext

    return extension_info
