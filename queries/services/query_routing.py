from .query_plan import QueryPlan


def should_run_in_background(
    *,
    query: QueryPlan,
) -> bool:

    sql_upper = query.analysis_sql.upper()

    heavy_keywords = [
        "GROUP BY",
        "HAVING",
        "OVER (",
        "UNION",
        "INTERSECT",
        "EXCEPT",
    ]

    join_count = sql_upper.count(
        " JOIN "
    )

    if join_count >= 2:
        return True

    if any(
        keyword in sql_upper
        for keyword in heavy_keywords
    ):
        return True

    return False