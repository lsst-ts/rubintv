import asyncio
from typing import Literal, Mapping, TypeAlias, TypedDict

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger
from ..handlers.websocket_notifiers import notify_redis_detector_status
from .redisstreamreader import StreamReader

logger = rubintv_logger()

# ----------------------------------------------------------------------
# Typed helpers
# ----------------------------------------------------------------------

StatusLiteral: TypeAlias = Literal["free", "busy", "missing", "queued"]


class QueueStatus(TypedDict, total=False):
    """Status for one detector entry.

    `queue_length` is present only when status == "queued".
    """

    status: StatusLiteral
    queue_length: int


# Text data is a simple mapping of strings to strings
TextData: TypeAlias = dict[str, str]

# A "numWorkers" entry is just an int, everything else is a QueueStatus
DecodedRedisValue: TypeAlias = Mapping[str, int | QueueStatus] | TextData

# detector‑name  ->  DecodedRedisValue | TextData
InitialData: TypeAlias = Mapping[str, DecodedRedisValue | TextData]

KeyspaceEvent: TypeAlias = Mapping[str, bytes]

# ----------------------------------------------------------------------
# Main handler
# ----------------------------------------------------------------------


class DetectorStatusHandler:
    """Read detector status updates from Redis streams."""

    def __init__(
        self,
        redis_client: redis.Redis,
        mapped_keys: list[dict[str, str]],
        text_keys: list[dict[str, str]],
    ) -> None:
        self.redis_client = redis_client
        # Convert keys to stream names
        self.stream_keys = {
            f"stream:{d['key']}": d["name"] for d in mapped_keys + text_keys
        }
        self.mapped_keys = {d["key"]: d["name"] for d in mapped_keys}
        self.text_keys = {d["key"]: d["name"] for d in text_keys}
        logger.info(
            "Initializing DetectorStatusHandler with streams:",
            stream_keys=self.stream_keys,
            mapped_keys=self.mapped_keys,
            text_keys=self.text_keys,
        )
        self._running = False
        self.reader: StreamReader[DecodedRedisValue] | None = None

    async def verify_streams(self) -> None:
        """Verify that our stream keys exist and contain data."""
        for stream_key in self.stream_keys.keys():
            try:
                # Check if stream exists and get its length
                length = await self.redis_client.xlen(stream_key)
                if length > 0:
                    # Get last entry for diagnostic purposes
                    last_entry = await self.redis_client.xrevrange(stream_key, count=1)
                    logger.info(
                        "Stream verified",
                        stream=stream_key,
                        length=length,
                        last_entry=last_entry,
                    )
                else:
                    logger.warning(f"Stream {stream_key} exists but is empty")
            except Exception as e:
                logger.error(f"Error checking stream {stream_key}: {e}")

    async def read_initial_state(self) -> None:
        """Read all entries from each stream to build complete initial state
        for each detector.
        """
        for stream_key, name in self.stream_keys.items():
            try:
                # Get all entries from the stream, oldest first
                entries = await self.redis_client.xrange(stream_key)
                if not entries:
                    logger.warning(f"No initial state found for stream {stream_key}")
                    continue

                # Build up state from all entries
                current_state: dict[str, int | QueueStatus | str] = {}

                # Process entries from oldest to newest
                for _, data in entries:
                    decoded = _decode_stream_message(data)

                    # For text status streams, update with non-empty values
                    if any(isinstance(v, str) for v in decoded.values()):
                        for k, v in decoded.items():
                            if v:  # Only add/update non-empty values
                                current_state[k] = v
                            elif k in current_state:  # Remove key if new value is empty
                                current_state.pop(k)
                        continue

                    # For worker status streams, update each detector's status
                    for detector_id, status in decoded.items():
                        current_state[detector_id] = status

                await notify_redis_detector_status({name: current_state})

            except Exception as e:
                logger.error(f"Error reading initial state from {stream_key}: {e}")

    async def run_async(self) -> None:
        """Start reading from streams."""
        await self.verify_streams()

        async def adapted_callback(name: str, data: DecodedRedisValue) -> None:
            """Adapt the decoded data to the format expected by
            notify_redis_detector_status."""
            await notify_redis_detector_status({name: data})

        self.reader = StreamReader[DecodedRedisValue](
            redis_client=self.redis_client,
            stream_keys=self.stream_keys,
            group_name="detector-status-group",
            consumer_name=f"detector-status-{id(self)}",
            decoder=_decode_stream_message,
            callback=adapted_callback,
        )
        self._running = True
        try:
            await self.reader.run()
        except asyncio.CancelledError:
            await self.stop_async()
            raise

    async def stop_async(self) -> None:
        """Stop reading from streams."""
        self._running = False
        if self.reader is not None:
            await self.reader.stop()


def _parse_worker_count(value: str) -> int:
    """Parse the worker count from a Redis value.

    Parameters
    ----------
    value : str
        The raw value from Redis

    Returns
    -------
    int
        The number of workers, defaulting to 0 if parsing fails
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _decode_stream_message(data: dict[bytes, bytes]) -> DecodedRedisValue:
    """Decode stream message into domain type."""

    detector_id = data[b"detector_id"].decode()
    status = data[b"status"].decode()
    entry_type = data[b"type"].decode()

    # Handle text-based status messages (like other queues)
    if entry_type == "text_status":
        return {detector_id: status}

    # Create a new detector status dict for worker statuses
    decoded_data: dict[str, int | QueueStatus] = {}

    # Handle based on entry type
    if entry_type == "worker_count":
        decoded_data["numWorkers"] = _parse_worker_count(status)
    else:
        try:
            queue_length = int(status)  # If status is a number, it's a queue length
            decoded_data[detector_id] = {
                "status": "queued",
                "queue_length": queue_length,
            }
        except ValueError:
            if status in ("free", "busy", "missing"):
                decoded_data[detector_id] = {"status": status}  # type: ignore
            else:
                logger.debug(
                    "Detector %s has unknown status string: %s", detector_id, status
                )

    return decoded_data
