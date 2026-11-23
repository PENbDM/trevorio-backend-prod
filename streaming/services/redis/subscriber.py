
import os
import redis.asyncio as redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USE_TLS = os.getenv("REDIS_USE_TLS", "false").lower() == "true"

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    **(
        {
            "ssl": True,
            "ssl_cert_reqs": "required",
        }
        if REDIS_USE_TLS
        else {}
    ),
)


async def subscribe():
    async with r.pubsub() as pubsub:
        await pubsub.subscribe("detection")

        print("SSE subscribed to Redis detection channel", flush=True)

        async for message in pubsub.listen():
            if message["type"] == "message":
                print("SSE RECEIVED:", message["data"], flush=True)
                yield message["data"]
