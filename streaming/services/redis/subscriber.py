import os
import redis.asyncio as redis

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    db=0,
    decode_responses=True
)

async def subscribe():
    async with r.pubsub() as pubsub:
        await pubsub.subscribe("detection")

        print("SSE subscribed to Redis detection channel", flush=True)

        async for message in pubsub.listen():
            if message["type"] == "message":
                print("SSE RECEIVED:", message["data"], flush=True)
                yield message["data"]