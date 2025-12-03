from typing import Any

import redis.asyncio as redis  # type: ignore[import]
from lsst.ts.rubintv.config import rubintv_logger
from lsst.ts.rubintv.handlers.websocket_notifiers import notify_controls_readback_change

logger = rubintv_logger()


class RedisSubscriber:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis_client = redis_client

    async def subscribe_to_keys(self, keys: list[str]) -> Any:
        """Subscribe to notifications for specific key patterns.

        Parameters
        ----------
        keys: `list` `[`str`]
            List of key patterns to monitor.

        Returns
        -------
        `dict`
            Redis PubSub object.
        """
        pubsub = self.redis_client.pubsub()

        # Subscribe to keyspace notifications for each pattern
        for key in keys:
            # Format: __keyspace@{db}__:{key_pattern}
            channel = f"__keyspace@0__:{key}"
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to keyspace events for key: {key}")

        return pubsub

    async def listen(self, pubsub: Any) -> None:
        """Listen for keyspace notifications and retrieve updated values.
        Parameters
        ----------
        pubsub: `dict`
            Redis PubSub object.
        """
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await self.handle_keyspace_event(message)

    async def handle_keyspace_event(self, message: dict[str, Any]) -> None:
        """Handle keyspace notification and retrieve the new value.
        Notifications are sent when keys are modified in Redis.

        Parameters
        ----------
        message: `dict`
            Message received from Redis PubSub.
        """
        # Extract key from channel name
        # Channel format: __keyspace@0__:actual_key
        channel = message.get("channel", b"").decode("utf-8")
        event_type = message.get("data", b"").decode("utf-8")

        if not channel.startswith("__keyspace@"):
            return

        # Extract the actual key that changed
        key = channel.split(":", 1)[1]
        logger.info(f"Key changed: {key}, Event: {event_type}")

        # Get the new value if it's a SET operation
        if event_type in ("set", "hset"):
            raw_value = await self.redis_client.get(key)
            value = raw_value.decode("utf-8") if raw_value else None
            logger.info(f"New value: {value}")
            await notify_controls_readback_change({"key": key, "value": value})

    async def stop(self, pubsub: Any) -> None:
        """Unsubscribe from all channels and close the PubSub connection."""
        await pubsub.unsubscribe()
        await pubsub.close()
        logger.info("Unsubscribed from all channels and closed PubSub connection.")
