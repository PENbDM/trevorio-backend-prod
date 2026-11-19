from celery import shared_task

from data_sources.models import DataSource

from .services.query_builder import build_query
from .services.raw_query import build_raw_query
from .services.query_runner import execute_query


@shared_task
def run_query_background(
    datasource_id,
    table_id,
    column_ids,
    filters,
    order_by,
    page,
    page_size,
    mode="browse",
):
    datasource = DataSource.objects.get(
        id=datasource_id
    )

    # --------------------------------
    # BROWSE MODE / LATEST MODE
    # --------------------------------
    # browse -> ORDER BY primary_key ASC
    # latest -> ORDER BY primary_key DESC
    #
    # The actual sorting is handled
    # inside build_query().
    #
    # Explicit order_by takes priority
    # over the default mode sorting.

    query = build_query(
        datasource=datasource,
        table_id=table_id,
        column_ids=column_ids,
        filters=filters,
        order_by=order_by,
        page=page,
        page_size=page_size,
        mode=mode,
    )

    # --------------------------------
    # EXECUTE QUERY
    # --------------------------------
    result = execute_query(
        datasource=datasource,
        query=query,
    )

    return result


@shared_task
def run_raw_query_background(
    datasource_id,
    raw_sql,
    page,
    page_size,
):
    datasource = DataSource.objects.get(
        id=datasource_id
    )

    # --------------------------------
    # RAW SQL QUERY
    # --------------------------------
    # Raw SQL has its own sorting.
    # Browse/latest mode does not apply.

    query = build_raw_query(
        raw_sql=raw_sql,
        page=page,
        page_size=page_size,
    )

    # --------------------------------
    # EXECUTE RAW SQL
    # --------------------------------
    result = execute_query(
        datasource=datasource,
        query=query,
    )

    return result