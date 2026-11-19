import redis.asyncio as redis

async def subscribe():
    r=redis.Redis(host='localhost',port=6379,db=0,decode_responses=True)
    async with r.pubsub() as pubsub:
        await pubsub.subscribe("detection")

        async for message in pubsub.listen():
            if message["type"] == "message":
                print(message)
                yield message["data"]

