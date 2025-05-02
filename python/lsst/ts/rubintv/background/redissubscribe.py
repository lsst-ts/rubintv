import asyncio
from typing import Any, Awaitable, Callable

import redis.asyncio as redis  # type: ignore[import]

from ..config import rubintv_logger

logger = rubintv_logger()


class KeyspaceSubscriber:
    """
    Subscribes to Redis keyspace notifications for specified keys.

    Requires Redis server configured with:
        CONFIG SET notify-keyspace-events K$
    """

    def __init__(
        self,
        client: redis.Redis,
        keys: list[str],
        callback: Callable[[dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """
        Parameters
        ----------
        client : redis.Redis
            Redis client instance
        keys : list[str]
            List of key names to subscribe to
        callback : Callable[[dict[str, Any]], Awaitable[Any]]
            Function to call on event: fn(event: dict)
        """
        self.client = client
        self.pubsub = self.client.pubsub(ignore_subscribe_messages=True)
        self.keys = keys
        self.callback = callback
        self._running: bool = False

    def _build_channels(self) -> list[str]:
        # Keyspace notifications publish to __keyspace@<db>__:<key>
        pattern = (
            "__keyspace@%d__:"
            % self.client.connection_pool.connection_kwargs.get("db", 0)
        )
        return [pattern + key for key in self.keys]

    async def start_async(self) -> None:
        """Start listening asynchronously"""
        self._running = True
        channels: list[str] = self._build_channels()

        # Subscribe to exact channels
        for ch in channels:
            await self.pubsub.subscribe(ch)
            logger.info(f"Subscribed to {ch}")

        # Start listening in the background
        asyncio.create_task(self._listen_async())

    async def _listen_async(self) -> None:
        """Listen for messages asynchronously"""
        while self._running:
            try:
                message = await self.pubsub.get_message()
                if message:
                    await self.callback(message)
                await asyncio.sleep(0.1)  # Prevent tight loop
            except Exception as e:
                logger.exception(f"Error in callback: {e}")
                if not self._running:
                    break

    async def stop_async(self) -> None:
        """Stop listening and clean up asynchronously"""
        self._running = False
        await self.pubsub.unsubscribe()
        await self.pubsub.aclose()
