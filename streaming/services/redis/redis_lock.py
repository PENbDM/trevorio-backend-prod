from trevorio.redis_client import r


def redisLock(datasource_id,table_id):
    lock = r.lock(
        f'lock:change-detector:{datasource_id}:{table_id}',
        timeout=60,
        blocking=False
    )
    return lock
