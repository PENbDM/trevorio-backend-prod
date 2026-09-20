import uuid

from django.conf import settings
from django.db import models


class DataSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    database_type = models.CharField(max_length=20, default="postgres")
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=5432)
    database_name = models.CharField(max_length=255)
    ssl_mode = models.CharField(max_length=20, default="prefer")
    secret_ref = models.CharField(max_length=500)
    status = models.CharField(max_length=20, default="connected")
    last_tested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_schema_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "data_sources_datasource"
        ordering = ("-created_at",)

    def __str__(self):
        return self.name


class DataSourceMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        COLLABORATOR = "collaborator", "Collaborator"

    datasource = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasource_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COLLABORATOR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_sources_datasourcemembership"

    def __str__(self):
        return f"{self.user_id}:{self.datasource_id}:{self.role}"


class DataSourceTable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    datasource = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="tables",
    )
    schema_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "data_sources_datasourcetable"
        ordering = ("schema_name", "name")

    def __str__(self):
        return f"{self.schema_name}.{self.name}"


class DataSourceColumn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        DataSourceTable,
        on_delete=models.CASCADE,
        related_name="columns",
    )
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=255)
    native_type = models.CharField(max_length=255)
    is_nullable = models.BooleanField(default=True)
    ordinal_position = models.IntegerField()
    is_primary_key = models.BooleanField(default=False)

    class Meta:
        db_table = "data_sources_datasourcecolumn"
        ordering = ("ordinal_position",)

    def __str__(self):
        return self.name
