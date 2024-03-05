from lsst.ts.rubintv.models.models import Event
from lsst.ts.rubintv.s3client import S3Client


async def get_metadata_obj(key: str, s3_client: S3Client) -> dict:
    if data := await s3_client.async_get_object(key):
        return data
    else:
        return {}


async def get_next_previous_from_table(
    table: dict[int, dict[str, dict]], event: Event
) -> tuple[dict | None, ...]:
    chan = event.channel_name
    chan_table = {}
    for seq, channels in table.items():
        if chan in channels:
            chan_table[seq] = table[seq][chan]
    if chan_table == {}:
        return (None, None)
    padded_seqs = [None, *chan_table.keys(), None]
    all_nxt_prv = tuple(zip(padded_seqs, padded_seqs[2:]))
    table_keys = all_nxt_prv[padded_seqs.index(event.seq_num) - 1]
    nxt_prv = tuple(
        [chan_table.get(seq) for seq in table_keys]  # type: ignore[arg-type]
    )
    return nxt_prv
