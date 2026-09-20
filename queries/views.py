from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from data_sources.access import accessible_datasources
from .serializers import RunQuerySerializer
from .services.query_runner import (
    QueryExecutionError,
    QueryValidationError,
    run_query,
)


class RunQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RunQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        datasource = get_object_or_404(
            accessible_datasources(request.user),
            id=data["datasource_id"],
        )

        try:
            result = run_query(
                datasource=datasource,
                table_id=data["table_id"],
                column_ids=data["column_ids"],
                filters=data.get("filters", []),
                order_by=data.get("order_by"),
                limit=data.get("limit", 100),
            )
        except QueryValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryExecutionError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)
