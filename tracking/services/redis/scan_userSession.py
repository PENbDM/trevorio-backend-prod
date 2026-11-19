import redis
from streaming.services.get_unique_tables import get_unique_tables


r= redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)

def scan_userSession():
    pipe = r.pipeline()

    res=list(r.scan_iter(f'user-session:*'))
    for key in res:
        pipe.hgetall(key)
    resultPipe=pipe.execute()
    dictionaryUserSession=dict(zip(res,resultPipe))
    return dictionaryUserSession





def main():
    session=scan_userSession()
    uniqe_tables=get_unique_tables(session)  ### function to do deduplication to get rid of session with same tables,
    ## to reduce query to db
    return session,uniqe_tables


if __name__ == "__main__":
    main()