# API contract used by the current frontend

Base URL: `http://127.0.0.1:8000`

## Login

`POST /api/auth/login/` or `/api/accounts/login/`

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "access": "...",
  "refresh": "...",
  "user": {
    "id": "7",
    "email": "user@example.com",
    "first_name": "Dmytro",
    "last_name": "Pen",
    "created_at": "..."
  }
}
```

## Me

`GET /api/auth/me/` or `/api/accounts/me/`

## Datasources

`GET /api/datasources/`

`POST /api/datasources/`

```json
{
  "name": "nike_db",
  "database_type": "postgres",
  "host": "localhost",
  "port": 5432,
  "database_name": "nike",
  "username": "postgres",
  "password": "secret",
  "ssl_mode": "disable"
}
```

Example response fields:

```json
{
  "id": "...",
  "name": "nike_db",
  "database_type": "postgres",
  "host": "localhost",
  "port": 5432,
  "database_name": "nike",
  "ssl_mode": "disable",
  "status": "connected",
  "role": "owner",
  "last_tested_at": "...",
  "last_schema_synced_at": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

## Schema

`GET /api/datasources/<uuid>/schema/`

```json
{
  "datasource_id": "...",
  "datasource_name": "nike_db",
  "last_schema_synced_at": "...",
  "tables": [
    {
      "id": "...",
      "schema_name": "public",
      "name": "orders",
      "columns": [
        {
          "id": "...",
          "name": "id",
          "data_type": "bigint",
          "native_type": "int8",
          "is_nullable": false,
          "ordinal_position": 1,
          "is_primary_key": true
        }
      ]
    }
  ]
}
```

`POST /api/datasources/<uuid>/sync-schema/`

## Run query

`POST /api/queries/run/`

```json
{
  "datasource_id": "...",
  "table_id": "...",
  "column_ids": ["..."],
  "filters": [
    {"column_id": "...", "operator": ">", "value": 10}
  ],
  "order_by": {"column_id": "...", "direction": "desc"},
  "limit": 100
}
```

Response:

```json
{
  "columns": [
    {"id": "...", "name": "id", "data_type": "bigint"}
  ],
  "rows": [
    {"id": 1}
  ],
  "row_count": 1,
  "limit": 100,
  "duration_ms": 12.34
}
```
