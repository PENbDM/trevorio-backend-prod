from rest_framework import serializers


class QueryFilterSerializer(serializers.Serializer):
    column_id = serializers.UUIDField()
    operator = serializers.ChoiceField(
        choices=("=", "!=", ">", ">=", "<", "<=", "contains", "is_null", "is_not_null")
    )
    value = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["operator"] not in ("is_null", "is_not_null") and "value" not in attrs:
            raise serializers.ValidationError(
                {"value": "This field is required for this operator."}
            )
        return attrs


class QueryOrderBySerializer(serializers.Serializer):
    column_id = serializers.UUIDField()
    direction = serializers.ChoiceField(choices=("asc", "desc"))


class RunQuerySerializer(serializers.Serializer):
    datasource_id = serializers.UUIDField()
    table_id = serializers.UUIDField()
    column_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    filters = QueryFilterSerializer(many=True, required=False, default=list)
    order_by = QueryOrderBySerializer(required=False, allow_null=True)
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
    )
    page_size = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=1000,
    )

class RunRawQuerySerializer(
    serializers.Serializer
):
    datasource_id = serializers.UUIDField()

    sql = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
    )
    page_size = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=1000,
    )