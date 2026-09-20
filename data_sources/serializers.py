from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    DataSource,
    DataSourceColumn,
    DataSourceMembership,
    DataSourceTable,
)
from .services.postgres import DatabaseConnectionError, test_connection_values
from .services.secret_store import SecretStoreError, get_secret_store


class DataSourceColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSourceColumn
        fields = (
            "id",
            "name",
            "data_type",
            "native_type",
            "is_nullable",
            "ordinal_position",
            "is_primary_key",
        )


class DataSourceTableSerializer(serializers.ModelSerializer):
    columns = DataSourceColumnSerializer(many=True, read_only=True)

    class Meta:
        model = DataSourceTable
        fields = ("id", "schema_name", "name", "columns")


class DataSourceSchemaSerializer(serializers.ModelSerializer):
    datasource_id = serializers.UUIDField(source="id", read_only=True)
    datasource_name = serializers.CharField(source="name", read_only=True)
    tables = DataSourceTableSerializer(many=True, read_only=True)

    class Meta:
        model = DataSource
        fields = (
            "datasource_id",
            "datasource_name",
            "last_schema_synced_at",
            "tables",
        )


class DataSourceSerializer(serializers.ModelSerializer):
    # Credentials are intentionally not model fields and are never returned.
    username = serializers.CharField(write_only=True, required=False, max_length=255)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    role = serializers.SerializerMethodField()

    class Meta:
        model = DataSource
        fields = (
            "id",
            "name",
            "database_type",
            "host",
            "port",
            "database_name",
            "username",
            "password",
            "ssl_mode",
            "status",
            "role",
            "last_tested_at",
            "last_schema_synced_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "role",
            "last_tested_at",
            "last_schema_synced_at",
            "created_at",
            "updated_at",
        )

    def get_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        return str(membership.role).lower() if membership else None

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()

        # Compatibility with previous frontend/backend naming iterations.
        if "database_name" not in data:
            if "database" in data:
                data["database_name"] = data.pop("database")
            elif "dbname" in data:
                data["database_name"] = data.pop("dbname")

        if "ssl_mode" not in data and "sslmode" in data:
            data["ssl_mode"] = data.pop("sslmode")

        if "database_type" not in data and "engine" in data:
            data["database_type"] = data.pop("engine")

        database_type = str(data.get("database_type", "postgres")).lower()
        if database_type == "postgresql":
            database_type = "postgres"
        data["database_type"] = database_type

        return super().to_internal_value(data)

    def validate_database_type(self, value):
        if value != "postgres":
            raise serializers.ValidationError("Only PostgreSQL is supported in the MVP.")
        return value

    def validate_ssl_mode(self, value):
        allowed = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid SSL mode. Use one of: {', '.join(sorted(allowed))}."
            )
        return value

    def validate(self, attrs):
        if self.instance is None:
            if not attrs.get("username"):
                raise serializers.ValidationError({"username": "This field is required."})
            if not attrs.get("password"):
                raise serializers.ValidationError({"password": "This field is required."})
        return attrs

    def _connection_values(self, validated_data, *, instance=None):
        secret_store = get_secret_store()
        old_credentials = {}
        if instance is not None:
            try:
                old_credentials = secret_store.get(instance.secret_ref)
            except SecretStoreError:
                old_credentials = {}

        username = validated_data.get("username") or old_credentials.get("username") or old_credentials.get("user")
        password = validated_data.get("password")
        if password is None:
            password = old_credentials.get("password")

        values = {
            "host": validated_data.get("host", getattr(instance, "host", None)),
            "port": validated_data.get("port", getattr(instance, "port", 5432)),
            "database_name": validated_data.get(
                "database_name", getattr(instance, "database_name", None)
            ),
            "username": username,
            "password": password,
            "ssl_mode": validated_data.get(
                "ssl_mode", getattr(instance, "ssl_mode", "prefer")
            ),
        }
        return values

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")

        try:
            test_connection_values(
                host=validated_data["host"],
                port=validated_data.get("port", 5432),
                database_name=validated_data["database_name"],
                username=username,
                password=password,
                ssl_mode=validated_data.get("ssl_mode", "prefer"),
            )
        except DatabaseConnectionError as exc:
            raise serializers.ValidationError({"connection": str(exc)}) from exc

        secret_ref = get_secret_store().put(
            {"username": username, "password": password}
        )

        datasource = DataSource.objects.create(
            secret_ref=secret_ref,
            status="connected",
            last_tested_at=timezone.now(),
            **validated_data,
        )
        DataSourceMembership.objects.create(
            datasource=datasource,
            user=self.context["request"].user,
            role=DataSourceMembership.Role.OWNER,
        )
        return datasource

    @transaction.atomic
    def update(self, instance, validated_data):
        username_supplied = "username" in validated_data
        password_supplied = "password" in validated_data
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)

        connection_fields_changed = bool(
            {"host", "port", "database_name", "ssl_mode", "database_type"}
            & set(validated_data.keys())
        )

        if username_supplied or password_supplied or connection_fields_changed:
            temp_data = dict(validated_data)
            if username_supplied:
                temp_data["username"] = username
            if password_supplied:
                temp_data["password"] = password
            values = self._connection_values(temp_data, instance=instance)

            if not values["username"] or values["password"] is None:
                raise serializers.ValidationError(
                    {"password": "Re-enter username and password for this datasource."}
                )

            try:
                test_connection_values(**values)
            except DatabaseConnectionError as exc:
                raise serializers.ValidationError({"connection": str(exc)}) from exc

            instance.secret_ref = get_secret_store().put(
                {"username": values["username"], "password": values["password"]}
            )
            instance.status = "connected"
            instance.last_tested_at = timezone.now()

        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance
