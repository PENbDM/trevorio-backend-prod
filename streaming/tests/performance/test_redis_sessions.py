from trevorio.redis_client import rPerformance
from time import perf_counter



def scan_userSession():
    dictionaryUserSession={}

    #Measure SCAN redis
    start_scan = perf_counter()
    res=list(rPerformance.scan_iter(f'user-session:*'))
    scan_time=perf_counter()-start_scan
    return res,scan_time

    #Measure HGETALL
    # start_hgetall=perf_counter()
    # count=0
    # #pipelining
    # pipe = rPerformance.pipeline()
    #
    # for key in res:
    #     pipe.hgetall(key)
    #     count+=1;
    # resultPipe=pipe.execute()
    # dictionaryUserSession = dict(zip(res, resultPipe)) # dict with session as key and object as a data
    # end=perf_counter()
    # executionTime=end-start_hgetall
    # return (
    #     f"Sessions: {count}",
    #     f"SCAN time: {scan_time:.4f}s",
    #     f"HGETALL time: {executionTime:.4f}s"
    # )



if __name__ == '__main__':
    result=scan_userSession()
    print(result)