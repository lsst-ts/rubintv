import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

import redis.asyncio as redis  # type: ignore[import]


async def simulate_burst_writes(
    redis_client: redis.Redis,
    stream_key: str,
    num_messages: int = 5,
    delay: float = 0.05,
) -> tuple[int, list[str]]:
    """Simulate a burst of writes to Redis"""
    burst_id = int(time.time() * 1000)  # unique burst identifier
    messages_written = []

    for i in range(num_messages):
        data = {
            "timestamp": time.time(),
            "burst_id": burst_id,
            "sequence": i,
            "test_data": f"burst_message_{i}",
        }
        msg_id = await redis_client.xadd(
            stream_key,
            {"data": json.dumps(data)},
            maxlen=1000,  # increased to retain more messages
        )
        messages_written.append(msg_id)
        print(f"{datetime.now().isoformat()} Wrote message {i} in burst {burst_id}")
        await asyncio.sleep(delay)

    return burst_id, messages_written


@asynccontextmanager
async def create_test_client() -> AsyncGenerator[redis.Redis, None]:
    client = await redis.Redis(host="localhost", port=6379, db=0)
    try:
        yield client
    finally:
        await client.aclose()


async def main() -> None:
    async with create_test_client() as redis_client:
        test_stream = "stream:test_stream"

        # Clear existing stream
        await redis_client.delete(test_stream)

        print(f"\n{datetime.now().isoformat()} Starting single message test")
        await redis_client.xadd(test_stream, {"data": json.dumps({"type": "single"})})

        # Add sleep to ensure message is processed
        await asyncio.sleep(0.1)

        print(f"\n{datetime.now().isoformat()} Starting burst test (5 messages)")
        burst_id, messages_written = await simulate_burst_writes(
            redis_client, test_stream
        )
        print(f"Completed burst {burst_id}, wrote {len(messages_written)} messages")

        # Add sleep between bursts
        await asyncio.sleep(0.2)

        print(f"\n{datetime.now().isoformat()} Starting rapid bursts test")
        total_messages = 0
        for i in range(3):  # Reduced to 3 bursts for clarity
            burst_id, messages = await simulate_burst_writes(
                redis_client, test_stream, num_messages=3, delay=0.02
            )
            total_messages += len(messages)
            print(f"Completed rapid burst {burst_id}, total messages: {total_messages}")
            await asyncio.sleep(0.2)  # Increased sleep between bursts

        # Verify final stream contents
        print(f"\n{datetime.now().isoformat()} Verifying stream contents")
        messages = await redis_client.xread({test_stream: "0-0"}, count=1000)
        if messages:
            stream_data = messages[0][1]
            print(f"Total messages in stream: {len(stream_data)}")

            # Print the last few message IDs to check ordering
            last_ids = []
            for msg in stream_data[-5:]:
                msg_id = msg[0]
                if isinstance(msg_id, bytes):
                    last_ids.append(msg_id.decode("utf-8"))
                else:
                    last_ids.append(str(msg_id))
            print(f"Last 5 message IDs: {last_ids}")


if __name__ == "__main__":
    asyncio.run(main())
