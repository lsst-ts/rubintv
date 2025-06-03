from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Generic, Mapping, TypeVar

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger

logger = rubintv_logger()

# T should be a Mapping type since we're dealing with dictionary states
T = TypeVar("T", bound=Mapping)

# Type alias for our state dictionary
StateDict = dict[str, T]

# Type aliases for message stats
MessageStats = dict[str, float | int]  # Changed to flatten the structure
StreamStats = dict[str, MessageStats]


class StreamReader(Generic[T]):
    """Reads latest data from Redis streams for real-time display."""

    MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB limit for messages

    def __init__(
        self,
        redis_client: redis.Redis,
        stream_keys: dict[str, str],
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
        decoder : Callable
            Function to decode raw Redis data into domain type T
        callback : Callable
            Async function to handle decoded messages
        """
        self.redis = redis_client
        self.stream_keys = stream_keys
        self.decoder = decoder
        self.callback = callback
        self._running = False
        # Initialize message stats with proper structure
        self._message_stats: StreamStats = {
            "last_message_time": {},
            "message_count": {},
            "burst_count": {},
        }

    async def _handle_messages(self, stream_key: str, messages: list) -> None:
        now = time.time()

        # Initialize stats for this stream if not present
        if stream_key not in self._message_stats["last_message_time"]:
            self._message_stats["last_message_time"][stream_key] = 0.0
        if stream_key not in self._message_stats["message_count"]:
            self._message_stats["message_count"][stream_key] = 0
        if stream_key not in self._message_stats["burst_count"]:
            self._message_stats["burst_count"][stream_key] = 0

        # Get current stats values
        last_time: float = self._message_stats["last_message_time"][stream_key]
        # Use float | int type to match what comes from the stats dictionary
        burst_count: float | int = self._message_stats["burst_count"][stream_key]
        message_count: float | int = self._message_stats["message_count"][stream_key]

        # Track true bursts (multiple messages received together)
        if len(messages) > 1:
            burst_count = int(burst_count) + 1  # Ensure int for counter
            self._message_stats["burst_count"][stream_key] = burst_count
            logger.info(
                "Processing burst",
                stream=stream_key,
                message_count=len(messages),
                time_since_last=now - last_time if last_time else None,
                burst_count=burst_count,
                message_ids=[msg[0].decode() for msg in messages],
            )
        elif (
            last_time and (now - last_time) < 0.025
        ):  # Threshold for rapid single messages
            logger.debug(
                "Rapid message",
                stream=stream_key,
                time_since_last=now - last_time,
                message_id=messages[0][0].decode(),
            )

        # Update message stats
        self._message_stats["last_message_time"][stream_key] = now
        self._message_stats["message_count"][stream_key] = message_count + len(messages)

        friendly_name = self.stream_keys[stream_key]

        for message_id, data in messages:
            try:
                # Basic size check to prevent memory issues
                data_size = sum(len(str(k)) + len(str(v)) for k, v in data.items())
                if data_size > self.MAX_MESSAGE_SIZE:
                    logger.error(
                        f"Message too large ({data_size} bytes) in stream {stream_key}, skipping",
                        message_id=message_id,
                    )
                    continue

                # Ensure all keys and values are bytes
                try:
                    data = {
                        k.encode() if isinstance(k, str) else k: (
                            v.encode() if isinstance(v, str) else v
                        )
                        for k, v in data.items()
                    }
                except (AttributeError, TypeError) as e:
                    logger.error(
                        f"Invalid data format in stream {stream_key}",
                        error=str(e),
                        data=str(data)[:200],
                    )
                    continue

                # Decode the full state update
                decoded_data = self.decoder(data)

                # Callback for each message individually
                try:
                    await self.callback(friendly_name, decoded_data)
                except Exception as e:
                    logger.error(
                        f"Error in callback for {stream_key}",
                        message_id=message_id,
                        error=str(e),
                        exc_info=True,
                    )

            except Exception:
                logger.error(
                    f"Error processing message {message_id}",
                    exc_info=True,
                    stream_key=stream_key,
                    data=str(data)[:200] if "data" in locals() else None,
                )

    async def run(self) -> None:
        """Start reading latest messages from streams."""
        self._running = True

        # Start from the beginning of each stream
        streams = {key: "0-0" for key in self.stream_keys}

        while self._running:
            try:
                messages = await self.redis.xread(
                    streams=streams,
                    count=10,
                    block=100,
                )

                if messages:
                    # Process messages concurrently
                    tasks = []
                    for stream, stream_messages in messages:
                        stream_key = stream.decode()
                        # Update our last seen ID immediately
                        if stream_messages:
                            streams[stream_key] = stream_messages[-1][0]
                        # Create task for message processing
                        tasks.append(
                            asyncio.create_task(
                                self._handle_messages(stream_key, stream_messages)
                            )
                        )
                    # Wait for all processing to complete
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                # Small sleep to prevent tight loop when no messages
                await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error reading from streams: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop reading from streams."""
        self._running = False
