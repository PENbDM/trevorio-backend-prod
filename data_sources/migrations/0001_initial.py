import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("database_type", models.CharField(default="postgres", max_length=20)),
                ("host", models.CharField(max_length=255)),
                ("port", models.IntegerField(default=5432)),
                ("database_name", models.CharField(max_length=255)),
                ("ssl_mode", models.CharField(default="prefer", max_length=20)),
                ("secret_ref", models.CharField(max_length=500)),
                ("status", models.CharField(default="connected", max_length=20)),
                ("last_tested_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_schema_synced_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "data_sources_datasource",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="DataSourceTable",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("schema_name", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("datasource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tables", to="data_sources.datasource")),
            ],
            options={
                "db_table": "data_sources_datasourcetable",
                "ordering": ("schema_name", "name"),
            },
        ),
        migrations.CreateModel(
            name="DataSourceMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("collaborator", "Collaborator")], default="collaborator", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("datasource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="data_sources.datasource")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="datasource_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "data_sources_datasourcemembership"},
        ),
        migrations.CreateModel(
            name="DataSourceColumn",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("data_type", models.CharField(max_length=255)),
                ("native_type", models.CharField(max_length=255)),
                ("is_nullable", models.BooleanField(default=True)),
                ("ordinal_position", models.IntegerField()),
                ("is_primary_key", models.BooleanField(default=False)),
                ("table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="columns", to="data_sources.datasourcetable")),
            ],
            options={
                "db_table": "data_sources_datasourcecolumn",
                "ordering": ("ordinal_position",),
            },
        ),
    ]
