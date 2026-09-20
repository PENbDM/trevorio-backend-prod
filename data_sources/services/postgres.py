import psycopg

from .secret_store import SecretStoreError, get_secret_store


class DatabaseConnectionError(Exception):
    pass


def _credentials(datasource):
    try:
        payload = get_secret_store().get(datasource.secret_ref)
    except SecretStoreError as exc:
        raise DatabaseConnectionError(str(exc)) from exc

    username = payload.get("username") or payload.get("user")
    password = payload.get("password")
    if not username or password is None:
        raise DatabaseConnectionError("Stored datasource credentials are incomplete.")
    return username, password


def connection_kwargs(datasource):
    username, password = _credentials(datasource)
    return {
        "host": datasource.host,
        "port": datasource.port,
        "dbname": datasource.database_name,
        "user": username,
        "password": password,
        "sslmode": datasource.ssl_mode or "prefer",
        "connect_timeout": 5,
    }


def test_connection_values(
    *,
    host,
    port,
    database_name,
    username,
    password,
    ssl_mode="prefer",
):
    try:
        with psycopg.connect(
            host=host,
            port=port,
            dbname=database_name,
            user=username,
            password=password,
            sslmode=ssl_mode or "prefer",
            connect_timeout=5,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:
        raise DatabaseConnectionError("Unable to connect to the database.") from exc
