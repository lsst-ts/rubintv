from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Generic, TypeVar

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger

logger = rubintv_logger()

T = TypeVar("T")


class StreamReader(Generic[T]):
    """Reads data from Redis streams with guaranteed delivery."""

    def __init__(
        self,
        redis_client: redis.Redis,
        stream_keys: dict[str, str],  # Map of stream names to their friendly names
        group_name: str,
        consumer_name: str,
        decoder: Callable[[dict[bytes, bytes]], T],
        callback: Callable[[str, T], Awaitable[None]],
    ) -> None:
        """Initialize stream reader.

        Parameters
        ----------
        redis_client : redis.Redis
            Connected Redis client
        stream_keys : dict[str, str]
            Mapping of stream keys to friendly names
        group_name : str
            Consumer group name
        consumer_name : str
            Unique consumer name within the group
        decoder : Callable
            Function to decode raw Redis data into domain type T
        callback : Callable
            Async function to handle decoded messages
        """
        self.redis = redis_client
        self.stream_keys = stream_keys
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.decoder = decoder
        self.callback = callback
        self._running = False
        self._task: asyncio.Task | None = None

    async def setup_consumer_group(self) -> None:
        """Ensure consumer group exists for each stream."""
        for stream_key in self.stream_keys:
            try:
                # Create consumer group if it doesn't exists, starting from
                # earliest message
                await self.redis.xgroup_create(
                    stream_key, self.group_name, id="0", mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

    async def _process_pending(self) -> None:
        """Process any pending messages from previous sessions."""
        for stream_key in self.stream_keys:
            while True:
                # Get pending messages for this consumer
                pending = await self.redis.xpending_range(
                    stream_key,
                    self.group_name,
                    min="-",
                    max="+",
                    count=10,
                    consumername=self.consumer_name,
                )
                if not pending:
                    break

                # Claim and process pending messages
                for p in pending:
                    message_id = p["message_id"]
                    messages = await self.redis.xclaim(
                        stream_key,
                        self.group_name,
                        self.consumer_name,
                        min_idle_time=0,
                        message_ids=[message_id],
                    )
                    await self._handle_messages(stream_key, messages)

    async def _handle_messages(self, stream_key: str, messages: list) -> None:
        """Process messages and acknowledge them only after successful
        processing."""
        for message_id, data in messages:
            try:
                decoded_data = self.decoder(data)
                friendly_name = self.stream_keys[stream_key]
                await self.callback(friendly_name, decoded_data)
                # Acknowledge only after successful processing
                await self.redis.xack(stream_key, self.group_name, message_id)
            except Exception as e:
                logger.exception(f"Error processing message {message_id}: {e}")

    async def run(self) -> None:
        """Start reading from streams."""
        await self.setup_consumer_group()
        await self._process_pending()

        self._running = True
        streams = {key: ">" for key in self.stream_keys}

        while self._running:
            try:
                messages = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams=streams,
                    count=10,
                    block=1000,
                )

                if messages:
                    for stream, stream_messages in messages:
                        stream_key = stream.decode()
                        await self._handle_messages(stream_key, stream_messages)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error reading from streams: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop reading from streams."""
        self._running = False
