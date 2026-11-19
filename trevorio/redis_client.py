#trevor io data
import redis
r=redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)

#test performance
import redis
rPerformance=redis.Redis(host='localhost', port=6380, db=0,decode_responses=True)

