
test_data=[{'dbname': 'nike', 'user': 'postgres', 'password': '12Dimabob122',
            'host': 'nikedatabase.c70yea6cqqb2.eu-west-2.rds.amazonaws.com', 'port': 5432, 'sslmode': 'require',
            'datasource_id': 'f4838bba-6a10-48bb-a006-5bc74499a887', 'table_id': 'f9d05dbf-ee5d-498d-b998-b23942915705',
            'table_name': 'orders'},
           {'dbname': 'nike', 'user': 'postgres', 'password': '12Dimabob122',
            'host': 'nikedatabase.c70yea6cqqb2.eu-west-2.rds.amazonaws.com', 'port': 5432, 'sslmode': 'require',
            'datasource_id': 'f4838bba-6a10-48bb-a006-5bc74499a887', 'table_id': '0e2a5583-ce19-43eb-8f5f-597c8ab03e77',
            'table_name': 'users'},
           {'dbname': 'nike', 'user': 'postgres', 'password': '12Dimabob122',
            'host': 'nikedatabase.c70yea6cqqb2.eu-west-2.rds.amazonaws.com', 'port': 5432, 'sslmode': 'require',
            'datasource_id': 'f4838bba-6a10-48bb-a006-5bc74499a885', 'table_id': 'd6cf2ce6-763f-4197-aea6-ab5a7d7810f9a',
            'table_name': 'users'}]



def group_datasource_id_test(test_data):
    dictionary={}
    for data in test_data:
        if data['datasource_id'] not in dictionary:
            dictionary[data['datasource_id']] = [data]
        else:
            dictionary[data['datasource_id']].append(data)
    return dictionary



# print(group_datasource_id_test(test_data))

