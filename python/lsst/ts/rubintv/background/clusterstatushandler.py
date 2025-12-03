import asyncio
import json
from typing import Literal, TypeAlias, TypedDict

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger
from ..handlers.websocket_notifiers import notify_redis_detector_status
from .redisstreamreader import StreamReader

logger = rubintv_logger()

# ----------------------------------------------------------------------
# Typed helpers
# ----------------------------------------------------------------------

# Status values for a worker
StatusLiteral: TypeAlias = Literal[
    "free", "busy", "missing", "queued", "restarting", "guest"
]


class QueueStatus(TypedDict, total=False):
    status: StatusLiteral
    queue_length: int


# Workers mapping: worker name -> QueueStatus
WorkersDict: TypeAlias = dict[str, QueueStatus]

# Text status mapping: key -> text value
TextStatusDict: TypeAlias = dict[str, str]

# The decoded Redis value can contain:
# - "workers": mapping of worker names to their status
# - "text": mapping of keys to text status
# - "numWorkers": integer count of workers
DecodedRedisValue: TypeAlias = dict[str, WorkersDict | TextStatusDict | int]

# Initial data: detector name -> DecodedRedisValue
InitialData: TypeAlias = dict[str, DecodedRedisValue]

# Keyspace event: mapping of string to bytes
KeyspaceEvent: TypeAlias = dict[str, bytes]

# ----------------------------------------------------------------------
# Main handler
# ----------------------------------------------------------------------


class DetectorStatusHandler:
    """Read detector status updates from Redis streams."""

    def __init__(
        self,
        redis_client: redis.Redis,
        redis_keys: list[dict[str, str]],
    ) -> None:
        self.redis_client = redis_client
        # Convert keys to stream names
        self.stream_keys = {f"stream:{d['key']}": d["name"] for d in redis_keys}
        logger.info(
            "Initializing DetectorStatusHandler with streams:",
            stream_keys=self.stream_keys,
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
        """Read the latest entry from each stream to get current state and
        send notifications.
        """
        for stream_key, name in self.stream_keys.items():
            try:
                # Get just the latest entry since we have maxlen=2
                entries = await self.redis_client.xrevrange(stream_key, count=1)
                if not entries:
                    logger.warning(f"No initial state found for stream {stream_key}")
                    continue
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

    async def get_current_state(self) -> dict[str, DecodedRedisValue] | None:
        """Get the current state from all streams for initial WebSocket
        payload.

        Returns
        -------
        `dict` [`str`, `DecodedRedisValue`] | None
            Dictionary mapping stream names to their current decoded state,
            or None if no state is available.
        """
        current_state = {}

        for stream_key, name in self.stream_keys.items():
            try:
                # Get just the latest entry since we have maxlen=2
                entries = await self.redis_client.xrevrange(stream_key, count=1)
                if not entries:
                    logger.warning(f"No current state found for stream {stream_key}")
                    continue

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
                current_state[name] = decoded

            except Exception as e:
                logger.error(
                    f"Error reading current state from {stream_key}: {e}",
                    exc_info=True,
                )

        return current_state if current_state else None

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
    data : `dict` [`bytes`, `bytes`]
        Raw Redis stream message data. Expected to contain a 'data' field
        with JSON encoded detector status information.

    Returns
    -------
    decoded : `DecodedRedisValue`
        Decoded message data in the expected format
    """
    try:
        # Get the JSON data from the 'data' field
        json_data = data[b"data"].decode()
        state_data = json.loads(json_data)

        if not isinstance(state_data, dict):
            logger.warning(f"Expected dict data, got {type(state_data)}")
            return {}

        # Use DecodedRedisValue for result type
        result: DecodedRedisValue = {}

        workers: WorkersDict = {}
        text: TextStatusDict = {}

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
                    workers[key] = {
                        "status": "queued",
                        "queue_length": queue_length,
                    }
                except ValueError:
                    # Handle as normal status
                    if status_value in (
                        "free",
                        "busy",
                        "missing",
                        "restarting",
                        "guest",
                    ):
                        workers[key] = {"status": status_value}
                    else:
                        workers[key] = {"status": "missing"}
            elif status_type == "text_status":
                # text status is passed through as-is
                text[key] = status_value
            elif status_type == "worker_count":
                try:
                    result["numWorkers"] = int(status_value)
                except ValueError:
                    logger.warning(f"Invalid worker count for {key}: {status_value}")

        if workers:
            result["workers"] = workers
        if text:
            result["text"] = text

        return result
    except Exception as e:
        logger.warning(f"Failed to decode state: {e}", exc_info=True)
        return {}
