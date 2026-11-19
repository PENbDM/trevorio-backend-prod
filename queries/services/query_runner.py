from datetime import date, datetime, time
from decimal import Decimal
from math import ceil
from time import perf_counter
from uuid import UUID

import psycopg

from django.conf import settings

from .query_plan import QueryPlan

from data_sources.services.postgres import (
    DatabaseConnectionError,
    connection_kwargs,
)


POSTGRES_TYPE_MAP = {
    16: "boolean",
    20: "bigint",
    21: "smallint",
    23: "integer",

    25: "text",

    700: "real",
    701: "double precision",

    1042: "char",
    1043: "varchar",

    1082: "date",
    1083: "time",

    1114: "timestamp",
    1184: "timestamptz",

    1700: "numeric",

    2950: "uuid",

    3802: "jsonb",
    114: "json",
}


class QueryExecutionError(Exception):
    pass


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(
        value,
        (date, datetime, time, UUID),
    ):
        return str(value)

    if isinstance(value, bytes):
        return value.hex()

    return value


def execute_query(
    *,
    datasource,
    query: QueryPlan,
):
    started = perf_counter()

    try:
        with psycopg.connect(
            **connection_kwargs(datasource)
        ) as conn:

            with conn.cursor() as cursor:

                #
                # Make customer queries read-only.
                #
                cursor.execute(
                    "SET TRANSACTION READ ONLY"
                )

                #
                # Prevent queries running forever.
                #
                cursor.execute(
                    """
                    SELECT set_config(
                        'statement_timeout',
                        %s,
                        true
                    )
                    """,
                    (
                        str(
                            settings.CUSTOMER_QUERY_TIMEOUT_MS
                        ),
                    ),
                )

                #
                # 1. COUNT TOTAL ROWS
                #
                if query.count_statement is not None:

                    cursor.execute(
                        query.count_statement,
                        query.count_params or [],
                    )

                    count_row = cursor.fetchone()

                    total_rows = (
                        count_row[0]
                        if count_row
                        else 0
                    )

                else:
                    #
                    # Temporary fallback for query plans
                    # which do not support pagination yet.
                    #
                    total_rows = None

                #
                # 2. EXECUTE CURRENT PAGE QUERY
                #
                cursor.execute(
                    query.statement,
                    query.params,
                )

                if cursor.description is None:
                    raise QueryExecutionError(
                        "Query did not return any columns."
                    )

                description = cursor.description

                #
                # Query itself should already contain:
                #
                # LIMIT page_size
                # OFFSET ...
                #
                # But keep this protection so Trevor never
                # loads an unexpected amount into memory.
                #
                max_rows = getattr(
                    settings,
                    "CUSTOMER_QUERY_MAX_ROWS",
                    1000,
                )

                page_size = min(
                    query.page_size,
                    max_rows,
                )

                rows = cursor.fetchmany(
                    page_size
                )

    except DatabaseConnectionError as exc:
        raise QueryExecutionError(
            str(exc)
        ) from exc

    except psycopg.Error as exc:
        raise QueryExecutionError(
            "Query execution failed."
        ) from exc

    duration_ms = round(
        (perf_counter() - started) * 1000,
        2,
    )

    #
    # BUILDER QUERY
    #
    if query.requested_columns:

        columns = [
            {
                "id": str(column.id),
                "name": column.name,
                "data_type": column.data_type,
            }
            for column in query.requested_columns
        ]

        column_names = [
            column.name
            for column in query.requested_columns
        ]

    #
    # RAW SQL
    #
    else:

        column_names = [
            column.name
            for column in description
        ]

        columns = [
            {
                "id": f"raw:{index}:{column.name}",
                "name": column.name,
                "data_type": POSTGRES_TYPE_MAP.get(
                    column.type_code,
                    f"unknown:{column.type_code}",
                ),
            }
            for index, column in enumerate(
                description
            )
        ]

    #
    # Convert database rows into JSON-safe dictionaries.
    #
    result_rows = [
        {
            column_names[index]: _json_safe(value)
            for index, value in enumerate(row)
        }
        for row in rows
    ]

    #
    # PAGINATION
    #
    if total_rows is not None:

        total_pages = (
            ceil(total_rows / page_size)
            if total_rows > 0
            else 0
        )

        has_next = (
            query.page < total_pages
        )

        has_previous = (
            query.page > 1
        )

    else:
        total_pages = None
        has_next = None
        has_previous = (
            query.page > 1
        )

    return {
        "columns": columns,

        "rows": result_rows,

        "row_count": len(result_rows),

        "pagination": {
            "page": query.page,
            "page_size": page_size,

            "total_rows": total_rows,
            "total_pages": total_pages,

            "has_next": has_next,
            "has_previous": has_previous,
        },

        "duration_ms": duration_ms,

        "source": query.source,
    }