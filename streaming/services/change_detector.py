
import psycopg
import json
import logging
from psycopg.rows import dict_row
from psycopg import sql
from time import perf_counter
import time
from streaming.services.serialize_rows import custom_serializer
from streaming.services.redis.redis_snapshot import save_snapshot, get_snapshot
from streaming.services.redis.compare_snapshots import compare_snapshots
from streaming.services.redis.publisher import publish
from streaming.services.get_connection_details import main
from streaming.services.redis.group_datasource_id_test import group_datasource_id_test
from streaming.services.redis.redis_lock import redisLock

def change_detector():
    credentials = main()

    if not credentials:
        print("No active sessions. Skipping change detection.")
        return

    # Group tables by datasource_id
    group_datasource_id = group_datasource_id_test(credentials)

    for datasource_group, credentials in group_datasource_id.items():

        # Get database credentials from the first table in the group
        db_config = credentials[0]
        # Measure PostgreSQL connection establishment
        start = perf_counter()
        try:
            with psycopg.connect(
                dbname=db_config["dbname"],
                user=db_config["user"],
                host=db_config["host"],
                port=db_config["port"],
                password=db_config["password"],
                sslmode=db_config["sslmode"],
                autocommit=True
            ) as conn:

                connection_time = perf_counter() - start
                print(f"Start Datasource {datasource_group}: {connection_time:.4f}s")
                # Reuse the same PostgreSQL connection for all tables
                for connection in credentials:
                    result=redisLock(connection['datasource_id'], connection["table_id"])

                    acquire=result.acquire(blocking=False)
                    if not acquire:
                        print("Another worker is processing this table. Skipping.")
                        continue
                    try:
                        # WORKER CRASH TEST:
                        # Lock is held for up to 60 seconds.
                        # Forcefully terminate Celery during this 25-second sleep.
                        # print("CRASH TEST: Lock acquired. Terminate Celery worker now.")
                        # time.sleep(25)
                        # print("CRASH TEST: Worker survived the 25-second sleep.")

                        dbname = connection["dbname"]
                        table_name = connection["table_name"]
                        table_id = connection["table_id"]

                        # STEP 1 — PostgreSQL query and error handling
                        try:
                            with conn.cursor(row_factory=dict_row) as cur:
                                cur.execute(
                                    sql.SQL("""
                                        SELECT *
                                        FROM {}
                                        ORDER BY id DESC
                                        LIMIT 3;
                                    """).format(
                                        sql.Identifier(connection["table_name"])
                                    )
                                )

                                newRows = cur.fetchall()

                        except psycopg.errors.UndefinedTable:
                            print(f'Table {connection["table_name"]} does not exist.')
                            continue

                        # STEP 2 — Get previous snapshot from Redis
                        oldRows = get_snapshot(dbname, table_name, table_id)

                        # STEP 3 — First snapshot
                        if oldRows is None:
                            serialized_rows = json.dumps(newRows, default=custom_serializer)
                            save_snapshot(serialized_rows, dbname, table_name, table_id)
                            continue

                        # STEP 4 — Compare snapshots
                        desialized_Rows = json.loads(oldRows)

                        isDetected = compare_snapshots(desialized_Rows, newRows)

                        notification = {
                            "datasource_id": connection["datasource_id"],
                            "table_id": connection["table_id"],
                            "new_row_ids": isDetected
                        }

                        logger = logging.getLogger(__name__)

                        if isDetected:
                            publish("detection", json.dumps(notification))
                        else:
                            logger.info(f'No changes detected for table {table_name}.')

                        # STEP 5 — Save new snapshot
                        serialized_rows = json.dumps(newRows, default=custom_serializer)
                        save_snapshot(serialized_rows, dbname, table_name, table_id)
                    finally:
                        if result.owned():
                            result.release()
        except psycopg.OperationalError:
            print(f'Datasource {datasource_group} connection failed.')
        continue

if __name__ == "__main__":
    change_detector()
