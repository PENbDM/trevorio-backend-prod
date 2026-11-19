
def get_unique_tables(dictionaryUserSession):
    sets = set()
    for session,value in dictionaryUserSession.items():
        pair = (value["datasource_id"], value["table_id"])

        sets.add(pair)
    return sets


# 'TYPE OF DATA'
# {('f4838bba-6a10-48bb-a006-5bc74499a887', 'd6cf2ce6-763f-4197-aea6-ab5a7d78109a')}