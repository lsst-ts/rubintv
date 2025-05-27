from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Dict, Generic, Mapping, TypeVar

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger

logger = rubintv_logger()

# T should be a Mapping type since we're dealing with dictionary states
T = TypeVar("T", bound=Mapping)

# Type alias for our state dictionary
StateDict = Dict[str, T]


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

    async def _handle_messages(self, stream_key: str, messages: list) -> None:
        """Process latest messages."""
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

            except Exception:
                logger.error(
                    f"Error processing message {message_id}",
                    exc_info=True,
                    stream_key=stream_key,
                    data=str(data)[:200] if "data" in locals() else None,
                )
        try:
            await self.callback(friendly_name, decoded_data)
        except Exception as e:
            logger.error(f"Error in callback for {stream_key}: {e}", exc_info=True)

    async def run(self) -> None:
        """Start reading latest messages from streams."""
        self._running = True

        # Start from the beginning of each stream (0-0 means start from first
        # message)
        streams = {key: "0-0" for key in self.stream_keys}

        while self._running:
            try:
                messages = await self.redis.xread(
                    streams=streams,
                    count=1,  # Get one message at a time to avoid memory issues
                    block=1000,
                )
                if messages:
                    for stream, stream_messages in messages:
                        stream_key = stream.decode()
                        await self._handle_messages(stream_key, stream_messages)
                        # Update our last seen ID to the latest message
                        if stream_messages:
                            streams[stream_key] = stream_messages[-1][0]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error reading from streams: {e}")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop reading from streams."""
        self._running = False
