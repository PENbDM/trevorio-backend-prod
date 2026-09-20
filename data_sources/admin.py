from django.contrib import admin

from .models import DataSource, DataSourceColumn, DataSourceMembership, DataSourceTable


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "database_type",
        "host",
        "database_name",
        "status",
        "last_tested_at",
    )
    search_fields = ("name", "host", "database_name")
    readonly_fields = ("secret_ref", "created_at", "updated_at", "last_schema_synced_at")


admin.site.register(DataSourceMembership)
admin.site.register(DataSourceTable)
admin.site.register(DataSourceColumn)
