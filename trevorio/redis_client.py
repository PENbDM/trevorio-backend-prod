import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

r = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    db=0,
    decode_responses=True
)   

#test performance
import redis
rPerformance=redis.Redis(host='host.docker.internal', port=6380, db=0,decode_responses=True)

