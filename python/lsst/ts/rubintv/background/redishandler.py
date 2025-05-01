import asyncio
import json
from typing import Any

import redis.asyncio as redis

from ..config import rubintv_logger
from ..handlers.websocket_notifiers import notify_redis_detector_status
from .redissubscribe import KeyspaceSubscriber

logger = rubintv_logger()


class DetectorStatusHandler:
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

        # The keys are expected to be string representations of JSON
        # objects
        if key_type != "string":
            logger.debug(f"Key {key} is not a string")
            return None

        value = await self.redis_client.get(key)
        if value is None:
            logger.debug(f"Key {key} does not exist")
            return None

        try:
            # Try to parse as JSON first
            data = json.loads(value.decode())
        except json.JSONDecodeError:
            # If not JSON, return nothing
            logger.debug(f"Key {key} is not JSON")
            return None
        if not isinstance(data, dict):
            logger.debug(f"Key {key} is not a JSON object")
            logger.debug(f"Key {key} value: {data}")
            return None

        # Unpack the data into a dict with keys as strings
        # and values as dicts with "status" and "queue_length"
        # or "status" and the original value
        unpacked_data = {}
        for k, v in data.items():
            try:
                v = int(v)
                unpacked_data[k] = {"status": "queued", "queue_length": v}
            except ValueError:
                # If the value cannot be cast to an int, we assume it's a
                # string and create a nested dict with key "status" and the
                # original value
                unpacked_data[k] = {"status": v}
        return unpacked_data

    async def read_initial_data(
        self,
    ) -> dict[str, str | list[str] | dict[str, Any]]:
        """Read initial data for all subscribed keys and notify clients"""
        logger.debug("Reading initial data for all keys", key=self.keys)
        data = {}
        for key in self.keys:
            try:
                decoded_value = await self._decode_redis_value(key)
                if decoded_value is not None:
                    set_name = self.mapped_keys[key]
                    data[set_name] = decoded_value
            except Exception as e:
                logger.debug(f"Error reading initial data for {key}: {e}")
        return data

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
