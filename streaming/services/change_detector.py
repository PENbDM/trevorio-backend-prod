
import psycopg
import json
import logging
from psycopg.rows import dict_row
from psycopg import sql
from time import perf_counter

from streaming.services.serialize_rows import custom_serializer
from streaming.services.redis.redis_snapshot import save_snapshot, get_snapshot
from streaming.services.redis.compare_snapshots import compare_snapshots
from streaming.services.redis.publisher import publish
from streaming.services.get_connection_details import main
from streaming.services.redis.group_datasource_id_test import group_datasource_id_test
from streaming.services.redis.redis_lock import redisLock


logger = logging.getLogger(__name__)


def change_detector():
    credentials = main()

    if not credentials:
        logger.info("No active sessions. Skipping change detection.")
        return

    # Group tables by datasource_id
    grouped_datasources = group_datasource_id_test(credentials)

    for datasource_group, connections in grouped_datasources.items():

        db_config = connections[0]
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

                logger.info(
                    "Datasource %s connected in %.4fs",
                    datasource_group,
                    connection_time
                )

                # Reuse PostgreSQL connection for all tables
                for connection in connections:

                    datasource_id = connection["datasource_id"]
                    table_id = connection["table_id"]
                    table_name = connection["table_name"]
                    dbname = connection["dbname"]

                    lock = redisLock(datasource_id, table_id)

                    acquired = lock.acquire(blocking=False)

                    if not acquired:
                        logger.info(
                            "Another worker is processing table %s. Skipping.",
                            table_name
                        )
                        continue

                    try:
                        # STEP 1 — Query PostgreSQL
                        try:
                            with conn.cursor(row_factory=dict_row) as cur:
                                cur.execute(
                                    sql.SQL("""
                                        SELECT *
                                        FROM {}
                                        ORDER BY id DESC
                                        LIMIT 3;
                                    """).format(
                                        sql.Identifier(table_name)
                                    )
                                )

                                newRows = cur.fetchall()

                        except psycopg.errors.UndefinedTable:
                            logger.warning(
                                "Table %s does not exist.",
                                table_name
                            )
                            continue

                        # STEP 2 — Read previous Redis snapshot
                        oldRows = get_snapshot(
                            dbname,
                            table_name,
                            table_id
                        )

                        # STEP 3 — Initialize first snapshot
                        if oldRows is None:
                            serialized_rows = json.dumps(
                                newRows,
                                default=custom_serializer
                            )

                            save_snapshot(
                                serialized_rows,
                                dbname,
                                table_name,
                                table_id
                            )
                            continue

                        # STEP 4 — Compare snapshots
                        deserialized_rows = json.loads(oldRows)

                        detected_ids = compare_snapshots(
                            deserialized_rows,
                            newRows
                        )

                        notification = {
                            "datasource_id": datasource_id,
                            "table_id": table_id,
                            "new_row_ids": detected_ids
                        }

                        if detected_ids:
                            publish(
                                "detection",
                                json.dumps(notification)
                            )

                            logger.info(
                                "Detected %d new rows in table %s.",
                                len(detected_ids),
                                table_name
                            )
                        else:
                            logger.info(
                                "No changes detected for table %s.",
                                table_name
                            )

                        # STEP 5 — Save updated snapshot
                        serialized_rows = json.dumps(
                            newRows,
                            default=custom_serializer
                        )

                        save_snapshot(
                            serialized_rows,
                            dbname,
                            table_name,
                            table_id
                        )

                    finally:
                        if lock.owned():
                            lock.release()

        except psycopg.OperationalError:
            logger.exception(
                "Datasource %s connection failed.",
                datasource_group
            )


if __name__ == "__main__":
    change_detector()
