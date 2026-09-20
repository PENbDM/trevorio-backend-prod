from datetime import date, datetime, time
from decimal import Decimal
from time import perf_counter
from uuid import UUID

import psycopg
from django.conf import settings
from psycopg import sql

from data_sources.models import DataSourceTable
from data_sources.services.postgres import DatabaseConnectionError, connection_kwargs


class QueryValidationError(Exception):
    pass


class QueryExecutionError(Exception):
    pass


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, time, UUID)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def run_query(*, datasource, table_id, column_ids, filters, order_by, limit):
    try:
        table = DataSourceTable.objects.get(id=table_id, datasource=datasource)
    except DataSourceTable.DoesNotExist as exc:
        raise QueryValidationError("Table does not belong to this datasource.") from exc

    columns = {
        str(column.id): column
        for column in table.columns.filter(id__in=column_ids)
    }
    requested = [columns.get(str(column_id)) for column_id in column_ids]
    if any(column is None for column in requested):
        raise QueryValidationError(
            "One or more selected columns do not belong to this table."
        )

    auxiliary_ids = [str(item["column_id"]) for item in filters]
    if order_by:
        auxiliary_ids.append(str(order_by["column_id"]))

    lookup = {
        str(column.id): column
        for column in table.columns.filter(id__in=auxiliary_ids)
    }
    if len(lookup) != len(set(auxiliary_ids)):
        raise QueryValidationError(
            "A filter or sort column does not belong to this table."
        )

    statement = sql.SQL("SELECT {fields} FROM {schema}.{table}").format(
        fields=sql.SQL(", ").join(sql.Identifier(column.name) for column in requested),
        schema=sql.Identifier(table.schema_name),
        table=sql.Identifier(table.name),
    )

    clauses = []
    params = []
    direct_operators = {
        "=": "=",
        "!=": "!=",
        ">": ">",
        ">=": ">=",
        "<": "<",
        "<=": "<=",
    }

    for item in filters:
        column = lookup[str(item["column_id"])]
        operator = item["operator"]
        identifier = sql.Identifier(column.name)

        if operator in direct_operators:
            clauses.append(
                sql.SQL("{} " + direct_operators[operator] + " %s").format(identifier)
            )
            params.append(item.get("value"))
        elif operator == "contains":
            clauses.append(sql.SQL("CAST({} AS TEXT) ILIKE %s").format(identifier))
            params.append(f"%{item.get('value', '')}%")
        elif operator == "is_null":
            clauses.append(sql.SQL("{} IS NULL").format(identifier))
        elif operator == "is_not_null":
            clauses.append(sql.SQL("{} IS NOT NULL").format(identifier))

    if clauses:
        statement += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses)

    if order_by:
        column = lookup[str(order_by["column_id"])]
        direction = sql.SQL("ASC" if order_by["direction"] == "asc" else "DESC")
        statement += sql.SQL(" ORDER BY {} ").format(sql.Identifier(column.name)) + direction

    statement += sql.SQL(" LIMIT %s")
    params.append(limit)

    started = perf_counter()
    try:
        with psycopg.connect(**connection_kwargs(datasource)) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (str(settings.CUSTOMER_QUERY_TIMEOUT_MS),),
                )
                cursor.execute(statement, params)
                rows = cursor.fetchall()
    except DatabaseConnectionError as exc:
        raise QueryExecutionError(str(exc)) from exc
    except Exception as exc:
        raise QueryExecutionError("Query execution failed.") from exc

    duration_ms = round((perf_counter() - started) * 1000, 2)
    result_rows = [
        {
            requested[index].name: _json_safe(value)
            for index, value in enumerate(row)
        }
        for row in rows
    ]

    return {
        "columns": [
            {
                "id": str(column.id),
                "name": column.name,
                "data_type": column.data_type,
            }
            for column in requested
        ],
        "rows": result_rows,
        "row_count": len(result_rows),
        "limit": limit,
        "duration_ms": duration_ms,
    }
