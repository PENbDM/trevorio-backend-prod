import os
import redis

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

# Performance testing only — local Redis instance
rPerformance = redis.Redis(
    host="host.docker.internal",
    port=6380,
    db=0,
    decode_responses=True,
)