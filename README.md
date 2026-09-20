# Trevor.io clone backend — PostgreSQL recovery build

This recovery build is designed for the **existing local PostgreSQL `trevorio` database** shown in your database diagram. It does not use SQLite and it does not add an `owner_id` column to `data_sources_datasource`.

## Database contract restored

### `accounts_user`
- `id` — bigint / Django `BigAutoField`
- email-based login
- `created_at`, `updated_at`

### `data_sources_datasource`
- `id` UUID
- `name`
- `database_type`
- `host`
- `port`
- `database_name`
- `ssl_mode`
- `secret_ref`
- `status`
- `last_tested_at`
- `created_at`
- `updated_at`
- `last_schema_synced_at`

There is intentionally **no `owner_id`, username, or password column** in this table.

### `data_sources_datasourcemembership`
Ownership/access is stored here:
- `id` bigint
- `datasource_id` UUID
- `user_id` bigint
- `role`: `owner`, `admin`, `collaborator`
- `created_at`

### schema metadata
- `data_sources_datasourcetable`: UUID table IDs
- `data_sources_datasourcecolumn`: UUID column IDs

## Auth endpoints
Both prefixes are supported so the frontend remains compatible:

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`
- `POST /api/auth/token/refresh/`

and aliases:

- `POST /api/accounts/register/`
- `POST /api/accounts/login/`
- `GET /api/accounts/me/`
- `POST /api/accounts/token/refresh/`

Protected requests use:

```http
Authorization: Bearer <access_token>
```

## Datasource endpoints

- `GET /api/datasources/`
- `POST /api/datasources/`
- `GET /api/datasources/<uuid>/`
- `PATCH /api/datasources/<uuid>/`
- `DELETE /api/datasources/<uuid>/`
- `GET /api/datasources/<uuid>/schema/`
- `POST /api/datasources/<uuid>/sync-schema/`

Frontend create payload:

```json
{
  "name": "aws",
  "database_type": "postgres",
  "host": "example.rds.amazonaws.com",
  "port": 5432,
  "database_name": "nike",
  "username": "postgres",
  "password": "secret",
  "ssl_mode": "require"
}
```

`username` and `password` are input-only. They are encrypted into `secret_ref`; they are not exposed by the API.

## Query endpoint

`POST /api/queries/run/`

```json
{
  "datasource_id": "<uuid>",
  "table_id": "<uuid>",
  "column_ids": ["<uuid>"],
  "filters": [],
  "limit": 100
}
```

Supported filter operators:

`=`, `!=`, `>`, `>=`, `<`, `<=`, `contains`, `is_null`, `is_not_null`.

Customer queries run inside a PostgreSQL read-only transaction with a statement timeout.

## Windows setup

From the project folder:

```powershell
py -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py check
python manage.py showmigrations accounts
python manage.py showmigrations data_sources
python manage.py check_trevor_schema
python manage.py runserver
```

### Important: preserve your existing database

Do **not** drop your `trevorio` database or tables. This project is built to match them.

The archive already includes migrations representing the current schema. If your PostgreSQL `django_migrations` table already marks `accounts.0001_initial` and `data_sources.0001_initial` as applied, do not recreate the tables.

Before running any migration command, check:

```powershell
python manage.py showmigrations accounts
python manage.py showmigrations data_sources
```

If migration history differs from the files in this archive, inspect it first rather than resetting the database.

## Secret compatibility

New datasource credentials are stored directly in `secret_ref` as an encrypted Fernet token prefixed with `local:`. The store also tries to read legacy unprefixed Fernet tokens and a few common local-reference formats. If an old `secret_ref` points to a secret file that was deleted together with the old backend, the database row can remain but those credentials must be entered again.
