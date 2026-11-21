from trevorio.redis_client import r


def publish(channel,message):
    return r.publish(channel,message)