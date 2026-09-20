import psycopg
from django.db import transaction
from django.utils import timezone

from data_sources.models import DataSourceColumn, DataSourceTable
from .postgres import DatabaseConnectionError, connection_kwargs


COLUMNS_SQL = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    (c.is_nullable = 'YES') AS is_nullable,
    c.ordinal_position
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema
 AND t.table_name = c.table_name
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
  AND t.table_type IN ('BASE TABLE', 'VIEW')
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""

PRIMARY_KEYS_SQL = """
SELECT
    kcu.table_schema,
    kcu.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
 AND tc.table_name = kcu.table_name
WHERE tc.constraint_type = 'PRIMARY KEY'
"""


def sync_datasource_schema(datasource):
    try:
        with psycopg.connect(**connection_kwargs(datasource)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(COLUMNS_SQL)
                columns = cursor.fetchall()
                cursor.execute(PRIMARY_KEYS_SQL)
                primary_keys = {(row[0], row[1], row[2]) for row in cursor.fetchall()}
    except DatabaseConnectionError:
        raise
    except Exception as exc:
        raise DatabaseConnectionError("Unable to read database schema.") from exc

    grouped = {}
    for (
        schema_name,
        table_name,
        column_name,
        data_type,
        native_type,
        is_nullable,
        ordinal_position,
    ) in columns:
        grouped.setdefault((schema_name, table_name), []).append(
            {
                "name": column_name,
                "data_type": data_type,
                "native_type": native_type or "",
                "is_nullable": bool(is_nullable),
                "ordinal_position": ordinal_position,
                "is_primary_key": (schema_name, table_name, column_name) in primary_keys,
            }
        )

    with transaction.atomic():
        existing_tables = {
            (table.schema_name, table.name): table
            for table in datasource.tables.all()
        }
        seen_table_ids = []

        for (schema_name, table_name), cols in grouped.items():
            table = existing_tables.get((schema_name, table_name))
            if table is None:
                table = DataSourceTable.objects.create(
                    datasource=datasource,
                    schema_name=schema_name,
                    name=table_name,
                )
            seen_table_ids.append(table.id)

            existing_columns = {column.name: column for column in table.columns.all()}
            seen_column_ids = []

            for col in cols:
                obj = existing_columns.get(col["name"])
                if obj is None:
                    obj = DataSourceColumn(table=table, name=col["name"])

                obj.data_type = col["data_type"]
                obj.native_type = col["native_type"]
                obj.is_nullable = col["is_nullable"]
                obj.ordinal_position = col["ordinal_position"]
                obj.is_primary_key = col["is_primary_key"]
                obj.save()
                seen_column_ids.append(obj.id)

            table.columns.exclude(id__in=seen_column_ids).delete()

        if seen_table_ids:
            datasource.tables.exclude(id__in=seen_table_ids).delete()
        else:
            datasource.tables.all().delete()

        datasource.last_schema_synced_at = timezone.now()
        datasource.status = "connected"
        datasource.save(
            update_fields=("last_schema_synced_at", "status", "updated_at")
        )

    return datasource
