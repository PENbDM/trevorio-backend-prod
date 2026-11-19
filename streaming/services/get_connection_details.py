from tracking.services.redis.scan_userSession import scan_userSession
from data_sources.models import DataSource, DataSourceTable
from data_sources.services.secret_store import get_secret_store
from tracking.services.redis.scan_userSession import main as get_active_tables
def get_connection_details(datasource_id, table_id):

    # Retrieve DataSource from Django ORM
    datasource = DataSource.objects.get(id=datasource_id)

    # Retrieve table information from Django ORM
    table = DataSourceTable.objects.get(
        id=table_id,
        datasource_id=datasource_id
    )

    # Decrypt database credentials
    credentials = get_secret_store().get(datasource.secret_ref)

    return {
        "dbname": datasource.database_name,
        "user": credentials["username"],
        "password": credentials["password"],
        "host": datasource.host,
        "port": datasource.port,
        "sslmode": datasource.ssl_mode,
        "datasource_id": str(datasource.id),  # NEW
        "table_id": str(table.id),
        "table_name": table.name,
    }


def main():
    response = get_active_tables()
    sessions, unique_tables = response

    if not unique_tables:
        print("No active sessions found.")
        return None


    listOfConnectionDetails = []
    for datasource_id, table_id in unique_tables:
        connection_details = get_connection_details(
            datasource_id,
            table_id
        )
        listOfConnectionDetails.append(connection_details)
    return listOfConnectionDetails


#MY NEXT TASK IS LIST OF CONNECTIONDETAILS IS LIST
## BEFORE IT WAS DICTIONARY DIFFERENT DATA TYPE SO NEED TO UPGRADE CHANGE_DETECTOR ITSELF


    # Temporary: process only the first active session
    # for session_key, session_data in sessions.items():
    #
    #     datasource_id = session_data["datasource_id"]
    #     table_id = session_data["table_id"]
    #
    #     connection_details = get_connection_details(
    #         datasource_id,
    #         table_id
    #     )
    #
    #     # print("Session:", session_key)
    #     # print("Database:", connection_details["dbname"])
    #     # print("Host:", connection_details["host"])
    #     # print("Table:", connection_details["table_name"])
    #
    #     return connection_details


if __name__ == "__main__":
    main()