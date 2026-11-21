from trevorio.redis_client import r



# {'dbname': 'nike', 'user': 'postgres', 'password': '12Dimabob122',
#  'host': 'nikedatabase.c70yea6cqqb2.eu-west-2.rds.amazonaws.com', 'port': 5432, 'sslmode': 'require',
#  'table_id': 'd6cf2ce6-763f-4197-aea6-ab5a7d78109a', 'table_name': 'products'}

def save_snapshot(value, db_name, table_name, table_id):
    snapshot_key = f'snapshot:{db_name}_{table_name}_{table_id}'
    return r.set(snapshot_key, value=value, ex=600)

def get_snapshot(db_name,table_name,table_id):
    snapshot_key=f'snapshot:{db_name}_{table_name}_{table_id}'

    return r.get(snapshot_key)











if __name__ == '__main__':
    result = get_snapshot()
