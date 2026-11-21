from trevorio.redis_client import r



def make_record(user_id,table_id,datasource_id):
    print("user_id:", user_id)
    print("table_id:", table_id)
    print("datasource_id:", datasource_id)
    r.hset(f'user-session:{user_id}', mapping={
        'user_id': user_id,
        "table_id": table_id,
        "datasource_id": datasource_id,
    })
    result = r.expire(f'user-session:{user_id}',60)

    res=r.ttl(f'user-session:{user_id}')
    print(res)