from django.core.management.base import BaseCommand
from django.db import connection


EXPECTED = {
    "accounts_user": {
        "id",
        "password",
        "last_login",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "updated_at",
    },
    "data_sources_datasource": {
        "id",
        "name",
        "database_type",
        "host",
        "port",
        "database_name",
        "ssl_mode",
        "secret_ref",
        "status",
        "last_tested_at",
        "created_at",
        "updated_at",
        "last_schema_synced_at",
    },
    "data_sources_datasourcemembership": {
        "id",
        "role",
        "created_at",
        "datasource_id",
        "user_id",
    },
    "data_sources_datasourcetable": {
        "id",
        "schema_name",
        "name",
        "datasource_id",
    },
    "data_sources_datasourcecolumn": {
        "id",
        "name",
        "data_type",
        "native_type",
        "is_nullable",
        "ordinal_position",
        "is_primary_key",
        "table_id",
    },
}


class Command(BaseCommand):
    help = "Compare the preserved PostgreSQL Trevor tables with the restored model contract."

    def handle(self, *args, **options):
        failed = False
        with connection.cursor() as cursor:
            for table_name, expected_columns in EXPECTED.items():
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    [table_name],
                )
                actual = {row[0] for row in cursor.fetchall()}

                if not actual:
                    failed = True
                    self.stdout.write(self.style.ERROR(f"{table_name}: table not found"))
                    continue

                missing = expected_columns - actual
                extra = actual - expected_columns

                if missing:
                    failed = True
                    self.stdout.write(
                        self.style.ERROR(
                            f"{table_name}: missing columns: {', '.join(sorted(missing))}"
                        )
                    )
                else:
                    self.stdout.write(self.style.SUCCESS(f"{table_name}: required columns OK"))

                if extra:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{table_name}: additional columns kept untouched: {', '.join(sorted(extra))}"
                        )
                    )

        if failed:
            self.stdout.write(self.style.ERROR("Schema check found mismatches."))
        else:
            self.stdout.write(self.style.SUCCESS("Trevor PostgreSQL schema matches the restored backend contract."))
