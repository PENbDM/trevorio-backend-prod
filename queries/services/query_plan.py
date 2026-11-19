from dataclasses import dataclass

@dataclass
class QueryPlan:
    statement: object
    params: list
    source: str
    requested_columns: list | None
    analysis_sql: str

    page: int = 1
    page_size: int = 100

    count_statement: object | None = None
    count_params: list | None = None