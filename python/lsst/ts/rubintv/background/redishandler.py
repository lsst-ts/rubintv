# detector_status_handler.py
from __future__ import annotations  # postpone evaluation of annotations (Python ≥3.7)

import asyncio
from typing import Literal, Mapping, TypeAlias, TypedDict

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger
from ..handlers.websocket_notifiers import notify_redis_detector_status
from .redissubscribe import KeyspaceSubscriber

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
    """Subscribe to Redis key-space notifications and forward structured status
    information to websocket clients."""

    def __init__(
        self,
        redis_client: redis.Redis,
        mapped_keys: list[dict[str, str]],
        text_keys: list[dict[str, str]],
    ) -> None:
        """
        Parameters
        ----------
        redis_client
            Connected **async** Redis client.
        mapped_keys
            Each item must contain ``{"key": "<redis key>", "name":
            "<detector name>"}``.
        """
        self.redis_client = redis_client
        self.keys: list[str] = [d["key"] for d in mapped_keys]
        self.keys.extend(d["key"] for d in text_keys)
        self.mapped_keys: dict[str, str] = {d["key"]: d["name"] for d in mapped_keys}
        self.text_keys: dict[str, str] = {d["key"]: d["name"] for d in text_keys}
        self._running = False
        self.subscriber: KeyspaceSubscriber | None = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_worker_count(self, value: str) -> int:
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

    async def _decode_redis_value(self, key: str) -> DecodedRedisValue | None:
        """Translate the raw Redis hash into a typed Python structure."""
        key_type = (await self.redis_client.type(key)).decode()
        if key_type != "hash":
            logger.debug("Key %s is not a hash", key)
            return None

        redis_data = await self.redis_client.hgetall(key)
        if not redis_data:
            logger.debug("Key %s does not exist or is empty", key)
            return None

        decoded_data: dict[str, int | QueueStatus] = {}
        for raw_key, raw_value in redis_data.items():
            key_str = raw_key.decode()
            value_str = raw_value.decode()

            if key_str in ("num_workers", "numWorkers"):
                decoded_data["numWorkers"] = self._parse_worker_count(value_str)
                continue

            try:
                queue_length = int(value_str)  # e.g., "15" -> queued / 15
                decoded_data[key_str] = {
                    "status": "queued",
                    "queue_length": queue_length,
                }
            except ValueError:
                if value_str in ("free", "busy", "missing"):
                    decoded_data[key_str] = {"status": value_str}  # type: ignore
                else:
                    logger.debug("Key %s has unknown status string: %s", key, value_str)

        return decoded_data

    async def _decode_text_data(self, key: str) -> TextData:
        """Translate the raw Redis hash into a typed Python structure."""
        text_data = await self.redis_client.hgetall(key)
        if not text_data:
            logger.debug("Key %s does not exist or is empty", key)
            return {}
        text_data = {k.decode(): v.decode() for k, v in text_data.items()}
        return text_data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def read_initial_data(self) -> InitialData | None:
        """Fetch the current value for every subscribed key (once)."""
        logger.debug("Reading initial data for keys: %s", self.keys)
        initial: dict[str, DecodedRedisValue] = {}
        for key in self.keys:
            try:
                if key in self.text_keys:
                    initial[self.text_keys[key]] = await self._decode_text_data(key)
                    continue
                decoded = await self._decode_redis_value(key)
                if decoded is not None:
                    initial[self.mapped_keys[key]] = decoded
            except Exception as exc:
                logger.debug("Error reading %s: %s", key, exc, exc_info=True)

        return initial or None

    async def on_event(self, event: KeyspaceEvent) -> None:
        """Handle a single Redis key-space notification."""
        try:
            set_key = event["channel"].split(b":", 1)[1].decode()
            # Add logging to debug what events we're receiving
            logger.debug(f"Received event for key {set_key}: {event}")

            if set_key in self.text_keys:
                # This is a text key
                text_data = await self._decode_text_data(set_key)
                logger.debug(f"Decoded text data: {text_data}")
                await notify_redis_detector_status({self.text_keys[set_key]: text_data})
                return

            decoded = await self._decode_redis_value(set_key)
            if decoded is not None:
                await notify_redis_detector_status({self.mapped_keys[set_key]: decoded})
        except Exception as exc:
            logger.debug("Error processing event: %s", exc, exc_info=True)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def run_async(self) -> None:
        """Start the subscription loop (cancellable)."""
        self.subscriber = KeyspaceSubscriber(
            client=self.redis_client,
            keys=self.keys,
            callback=self.on_event,
        )
        self._running = True
        try:
            await self.subscriber.start_async()
            while self._running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            await self.stop_async()
            raise

    async def stop_async(self) -> None:
        """Gracefully close the subscriber and mark the loop as stopped."""
        self._running = False
        if self.subscriber is not None:
            await self.subscriber.stop_async()
