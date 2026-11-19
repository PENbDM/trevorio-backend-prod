from psycopg import sql

from data_sources.models import DataSourceTable
from queries.exceptions import QueryValidationError
from queries.services.query_plan import QueryPlan


DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000


def build_query(
    *,
    datasource,
    table_id,
    column_ids,
    filters,
    order_by,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    mode: str = "browse",
):
    """
    Build a safe, parameterized PostgreSQL SELECT query.

    Modes:
    - browse: first rows, primary key ASC
    - latest: last rows, primary key DESC

    Explicit order_by overrides default sorting.
    """

    # --------------------------------------------
    # Validate pagination and mode
    # --------------------------------------------

    if mode not in {"browse", "latest"}:
        raise QueryValidationError(
            "Invalid query mode."
        )

    if page < 1:
        raise QueryValidationError(
            "Page must be at least 1."
        )

    if page_size < 1:
        raise QueryValidationError(
            "Page size must be at least 1."
        )

    page_size = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    # --------------------------------------------
    # Get table
    # --------------------------------------------

    try:
        table = DataSourceTable.objects.get(
            id=table_id,
            datasource=datasource,
        )
    except DataSourceTable.DoesNotExist as exc:
        raise QueryValidationError(
            "Table does not belong to this datasource."
        ) from exc

    # --------------------------------------------
    # Validate selected columns
    # --------------------------------------------

    columns = {
        str(column.id): column
        for column in table.columns.filter(
            id__in=column_ids
        )
    }

    requested = [
        columns.get(str(column_id))
        for column_id in column_ids
    ]

    if not requested:
        raise QueryValidationError(
            "At least one column must be selected."
        )

    if any(column is None for column in requested):
        raise QueryValidationError(
            "One or more selected columns do not belong to this table."
        )

    # --------------------------------------------
    # Resolve filtering and sorting columns
    # --------------------------------------------

    auxiliary_ids = [
        str(item["column_id"])
        for item in filters
    ]

    if order_by:
        auxiliary_ids.append(
            str(order_by["column_id"])
        )

    lookup = {
        str(column.id): column
        for column in table.columns.filter(
            id__in=auxiliary_ids
        )
    }

    if len(lookup) != len(set(auxiliary_ids)):
        raise QueryValidationError(
            "A filter or sort column does not belong to this table."
        )

    # --------------------------------------------
    # Build SELECT statement
    # --------------------------------------------

    statement = sql.SQL(
        """
        SELECT {fields}
        FROM {schema}.{table}
        """
    ).format(
        fields=sql.SQL(", ").join(
            sql.Identifier(column.name)
            for column in requested
        ),
        schema=sql.Identifier(table.schema_name),
        table=sql.Identifier(table.name),
    )

    # --------------------------------------------
    # Build COUNT statement
    # --------------------------------------------

    count_statement = sql.SQL(
        """
        SELECT COUNT(*)
        FROM {schema}.{table}
        """
    ).format(
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

    # --------------------------------------------
    # Apply filters
    # --------------------------------------------

    for item in filters:
        column = lookup[str(item["column_id"])]
        operator = item["operator"]
        identifier = sql.Identifier(column.name)

        if operator in direct_operators:
            clauses.append(
                sql.SQL(
                    "{} " + direct_operators[operator] + " %s"
                ).format(identifier)
            )

            params.append(item.get("value"))

        elif operator == "contains":
            clauses.append(
                sql.SQL(
                    "CAST({} AS TEXT) ILIKE %s"
                ).format(identifier)
            )

            params.append(
                f"%{item.get('value', '')}%"
            )

        elif operator == "is_null":
            clauses.append(
                sql.SQL("{} IS NULL").format(identifier)
            )

        elif operator == "is_not_null":
            clauses.append(
                sql.SQL("{} IS NOT NULL").format(identifier)
            )

        else:
            raise QueryValidationError(
                f"Unsupported operator: {operator}"
            )

    # --------------------------------------------
    # Apply WHERE to SELECT and COUNT
    # --------------------------------------------

    if clauses:
        where_clause = (
            sql.SQL(" WHERE ")
            + sql.SQL(" AND ").join(clauses)
        )

        statement += where_clause
        count_statement += where_clause

    # --------------------------------------------
    # ORDER BY: custom sorting or default mode
    # --------------------------------------------

    if order_by:
        # User selected a specific sorting column.
        # This takes priority over browse/latest mode.

        direction_value = order_by["direction"].lower()

        if direction_value not in {"asc", "desc"}:
            raise QueryValidationError(
                "Invalid sort direction."
            )

        column = lookup[
            str(order_by["column_id"])
        ]

        direction = sql.SQL(
            direction_value.upper()
        )

        statement += sql.SQL(
            " ORDER BY {} {}"
        ).format(
            sql.Identifier(column.name),
            direction,
        )

    else:
        # BROWSE MODE -> primary key ASC
        # LATEST MODE -> primary key DESC

        primary_key = table.columns.filter(
            is_primary_key=True
        ).first()

        if primary_key is None:
            raise QueryValidationError(
                "A primary key is required for default sorting."
            )

        direction = (
            "DESC" if mode == "latest" else "ASC"
        )

        statement += sql.SQL(
            " ORDER BY {} {}"
        ).format(
            sql.Identifier(primary_key.name),
            sql.SQL(direction),
        )

    # --------------------------------------------
    # Save COUNT query parameters
    # --------------------------------------------

    count_params = list(params)

    # --------------------------------------------
    # Apply pagination
    # --------------------------------------------

    statement += sql.SQL(
        """
        LIMIT %s
        OFFSET %s
        """
    )

    params.extend([
        page_size,
        offset,
    ])

    # --------------------------------------------
    # Analysis SQL for background task routing
    # --------------------------------------------

    analysis_parts = [
        "SELECT",
        "FROM",
    ]

    if filters:
        analysis_parts.append("WHERE")

    # Both modes now include ORDER BY.
    analysis_parts.append("ORDER BY")

    # --------------------------------------------
    # Return QueryPlan
    # --------------------------------------------

    return QueryPlan(
        statement=statement,
        params=params,
        source="builder",
        requested_columns=requested,
        analysis_sql=" ".join(analysis_parts),
        page=page,
        page_size=page_size,
        count_statement=count_statement,
        count_params=count_params,
    )