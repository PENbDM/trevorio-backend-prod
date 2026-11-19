import sqlparse

from psycopg import sql

from .query_builder import QueryValidationError
from .query_plan import QueryPlan


MAX_PAGE_SIZE = 1000
DEFAULT_PAGE_SIZE = 100


def build_raw_query(
    *,
    raw_sql: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> QueryPlan:
    raw_sql = raw_sql.strip()

    if not raw_sql:
        raise QueryValidationError(
            "SQL query cannot be empty."
        )

    if page < 1:
        raise QueryValidationError(
            "Page must be at least 1."
        )

    if page_size < 1:
        raise QueryValidationError(
            "Page size must be at least 1."
        )

    page_size = min(
        page_size,
        MAX_PAGE_SIZE,
    )

    statements = [
        statement.strip()
        for statement in sqlparse.split(raw_sql)
        if statement.strip()
    ]

    if len(statements) != 1:
        raise QueryValidationError(
            "Only one SQL statement can be executed at a time."
        )

    statement_text = statements[0]

    parsed = sqlparse.parse(
        statement_text
    )

    if not parsed:
        raise QueryValidationError(
            "Invalid SQL query."
        )

    if parsed[0].get_type() != "SELECT":
        raise QueryValidationError(
            "Only SELECT queries are allowed."
        )

    statement_text = statement_text.rstrip(";")

    offset = (
        page - 1
    ) * page_size

    paginated_statement = sql.SQL(
        """
        SELECT *
        FROM (
            {}
        ) AS trevor_query
        LIMIT %s
        OFFSET %s
        """
    ).format(
        sql.SQL(statement_text)
    )

    count_statement = sql.SQL(
        """
        SELECT COUNT(*)
        FROM (
            {}
        ) AS trevor_count
        """
    ).format(
        sql.SQL(statement_text)
    )

    return QueryPlan(
        statement=paginated_statement,
        params=[
            page_size,
            offset,
        ],
        source="raw_sql",
        requested_columns=None,
        analysis_sql=statement_text,

        page=page,
        page_size=page_size,

        count_statement=count_statement,
        count_params=[],
    )