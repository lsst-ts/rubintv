import asyncio
import json
from typing import Any

import redis.asyncio as redis

from ..config import rubintv_logger
from ..handlers.websocket_notifiers import notify_redis_detector_status
from .redissubscribe import KeyspaceSubscriber

logger = rubintv_logger()


class RedisHandler:
    def __init__(
        self, redis_client: redis.Redis, mapped_keys: list[dict[str, str]]
    ) -> None:
        """RedisHandler for subscribing to Redis keyspace notifications.
        This class handles the subscription to Redis keyspace notifications
        and processes the events asynchronously.

        Parameters
        ----------
        redis_client : redis.Redis
            Redis client instance.
        keys : dict
            List of keys to subscribe to. The keys should be in the format
        """
        self.redis_client = redis_client
        self.keys = [detector["key"] for detector in mapped_keys]
        self.mapped_keys = {
            detector["key"]: detector["name"] for detector in mapped_keys
        }
        self._running = False
        self.subscriber: KeyspaceSubscriber | None = None

    async def _decode_redis_value(
        self, key: str
    ) -> str | list[str] | dict[str, Any] | None:
        """Helper method to decode Redis values of different types.

        Parameters
        ----------
        key : str
            Redis key to decode

        Returns
        -------
        decoded_value : Union[str, list, dict]
            Decoded value from Redis
        """
        key_type = await self.redis_client.type(key)
        key_type = key_type.decode()

        if key_type == "string":
            value = await self.redis_client.get(key)
            if value:
                try:
                    # Try to parse as JSON first
                    return json.loads(value.decode())
                except json.JSONDecodeError:
                    # If not JSON, return as plain string
                    return value.decode()
            return "{}"
        elif key_type == "list":
            value = await self.redis_client.lrange(key, 0, -1)
            return [v.decode() for v in value]
        elif key_type == "set":
            value = await self.redis_client.smembers(key)
            return [v.decode() for v in value]
        elif key_type == "hash":
            value = await self.redis_client.hgetall(key)
            return {k.decode(): json.loads(v.decode()) for k, v in value.items()}
        else:
            logger.debug(f"Unsupported Redis type {key_type} for key {key}")
            return None

    async def read_initial_data(
        self,
    ) -> dict[str, str | list[str] | dict[str, Any]] | None:
        """Read initial data for all subscribed keys and notify clients"""
        for key in self.keys:
            try:
                decoded_value = await self._decode_redis_value(key)
                if decoded_value is not None:
                    set_name = self.mapped_keys[key]
                    return {set_name: decoded_value}
            except Exception as e:
                logger.debug(f"Error reading initial data for {key}: {e}")
        return None

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle Redis keyspace events

        Parameters
        ----------
        event : dict
            Redis keyspace notification event
        """
        try:
            # Extract the key from the channel name
            set_key = event["channel"].split(b":", 1)[1].decode()

            # Read the current value for the changed key
            decoded_value = await self._decode_redis_value(set_key)
            if decoded_value is not None:
                set_name = self.mapped_keys[set_key]
                # Format data to match expected structure
                formatted_data = {set_name: decoded_value}
                await notify_redis_detector_status(formatted_data)
        except Exception as e:
            logger.debug(f"Error processing event: {e}")

    async def run_async(self) -> None:
        """Async version of the run method"""
        self.subscriber = KeyspaceSubscriber(
            client=self.redis_client, keys=self.keys, callback=self.on_event
        )
        self._running = True
        try:
            # Start the subscriber in async mode
            await self.subscriber.start_async()

            # Keep the task alive until cancelled
            while self._running:
                await asyncio.sleep(0.1)  # Prevent tight loop

        except asyncio.CancelledError:
            self._running = False
            await self.stop_async()
            raise

    async def stop_async(self) -> None:
        """Async cleanup method"""
        self._running = False
        if self.subscriber:
            await self.subscriber.stop_async()
