import redis
r = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)

def publish(channel,message):
    return r.publish(channel,message)