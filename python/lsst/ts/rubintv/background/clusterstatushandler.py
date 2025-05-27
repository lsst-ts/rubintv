import asyncio
import json
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
        """Verify that our stream keys exist."""
        for stream_key in self.stream_keys.keys():
            try:
                # Just check if stream exists
                exists = await self.redis_client.exists(stream_key)
                if not exists:
                    logger.warning(f"Stream {stream_key} does not exist")
            except Exception as e:
                logger.error(f"Error checking stream {stream_key}: {e}")

    async def read_initial_state(self) -> None:
        """Read the latest entry from each stream to get current state."""
        for stream_key, name in self.stream_keys.items():
            try:
                # Get just the latest entry since we have maxlen=2
                entries = await self.redis_client.xrevrange(stream_key, count=1)
                if not entries:
                    logger.warning(f"No initial state found for stream {stream_key}")
                    break
                # Get the latest state
                _, raw_data = entries[0]
                # Convert the raw data into a dictionary with byte keys
                data = {
                    k.encode() if isinstance(k, str) else k: (
                        v.encode() if isinstance(v, str) else v
                    )
                    for k, v in raw_data.items()
                }

                decoded = _decode_stream_message(data)
                await notify_redis_detector_status({name: decoded})

            except Exception as e:
                logger.error(
                    f"Error reading initial state from {stream_key}: {e}",
                    exc_info=True,
                    raw_data=str(raw_data) if "raw_data" in locals() else None,
                )

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


def _decode_stream_message(data: dict[bytes, bytes]) -> DecodedRedisValue:
    """Decode stream message into domain type.

    Parameters
    ----------
    data : dict[bytes, bytes]
        Raw Redis stream message data. Expected to contain a 'data' field
        with JSON encoded detector status information.

    Returns
    -------
    DecodedRedisValue
        Decoded message data in the expected format
    """
    try:
        # Get the JSON data from the 'data' field
        json_data = data[b"data"].decode()
        state_data = json.loads(json_data)

        if not isinstance(state_data, dict):
            logger.warning(f"Expected dict data, got {type(state_data)}")
            return {}

        result: dict[str, QueueStatus | int] = {}

        # Process each detector entry
        for key, value in state_data.items():
            if not isinstance(value, dict):
                continue

            # Convert status format
            status_type = value.get("type", "")
            status_value = value.get("status", "unknown")

            if status_type == "worker_status":
                try:
                    # Try to parse as queue length
                    queue_length = int(status_value)
                    result[key] = {"status": "queued", "queue_length": queue_length}
                except ValueError:
                    # Handle as normal status
                    if status_value in (
                        "free",
                        "busy",
                        "missing",
                        "restarting",
                        "guest",
                    ):
                        result[key] = {"status": status_value}
                    else:
                        result[key] = {"status": "missing"}
            if status_type == "text_status":
                # text status is passed through as-is
                result[key] = status_value
            if status_type == "worker_count":
                try:
                    result[key] = int(status_value)
                except ValueError:
                    logger.warning(f"Invalid worker count for {key}: {status_value}")
        return result
    except Exception as e:
        logger.warning(f"Failed to decode state: {e}", exc_info=True)
        return {}
