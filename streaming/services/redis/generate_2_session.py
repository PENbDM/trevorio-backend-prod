import redis
r=redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)

r.hset(f'user-session:{6}', mapping={
    'user_id': 6,
    'table_id': '0e2a5583-ce19-43eb-8f5f-597c8ab03e77',
    'datasource_id': 'f4838bba-6a10-48bb-a006-5bc74499a887'
})


# 0e2a5583-ce19-43eb-8f5f-597c8ab03e77  - user


# f9d05dbf-ee5d-498d-b998-b23942915705 - orders da


# d6cf2ce6-763f-4197-aea6-ab5a7d78109a - products