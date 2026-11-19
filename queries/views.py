from django.shortcuts import get_object_or_404

from celery.result import AsyncResult

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from data_sources.access import accessible_datasources

from .serializers import (
    RunQuerySerializer,
    RunRawQuerySerializer,
)

from .services.query_builder import (
    QueryValidationError,
    build_query,
)

from .services.query_routing import (
    should_run_in_background,
)

from .services.query_runner import (
    QueryExecutionError,
    execute_query,
)

from .services.raw_query import (
    build_raw_query,
)

from .tasks import (
    run_query_background,
    run_raw_query_background,
)


class RunQueryView(APIView):
    permission_classes = [IsAuthenticated]

    # Default mode
    mode = "browse"

    def post(self, request):
        serializer = RunQuerySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        datasource = get_object_or_404(
            accessible_datasources(request.user),
            id=data["datasource_id"],
        )

        try:
            # --------------------------------
            # BROWSE MODE / LATEST MODE
            # --------------------------------
            # browse -> first rows, ASC
            # latest -> newest rows, DESC

            query = build_query(
                datasource=datasource,
                table_id=data["table_id"],
                column_ids=data["column_ids"],
                filters=data.get("filters", []),
                order_by=data.get("order_by"),
                page=data["page"],
                page_size=data["page_size"],

                # Pass mode to query builder
                mode=self.mode,
            )

            # --------------------------------
            # HEAVY QUERY -> CELERY
            # --------------------------------
            if should_run_in_background(query=query):
                task = run_query_background.delay(
                    str(datasource.id),
                    str(data["table_id"]),
                    [str(column_id) for column_id in data["column_ids"]],
                    data.get("filters", []),
                    data.get("order_by"),
                    data["page"],
                    data["page_size"],

                    # Pass mode to Celery
                    self.mode,
                )

                return Response(
                    {
                        "status": "queued",
                        "task_id": task.id,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # --------------------------------
            # LIGHTWEIGHT QUERY -> EXECUTE
            # --------------------------------
            result = execute_query(
                datasource=datasource,
                query=query,
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

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class RunRawQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RunRawQuerySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        datasource = get_object_or_404(
            accessible_datasources(
                request.user
            ),
            id=data["datasource_id"],
        )

        try:
            #
            # Build raw SQL query with pagination.
            #
            query = build_raw_query(
                raw_sql=data["sql"],
                page=data["page"],
                page_size=data["page_size"],
            )

            #
            # Heavy raw query -> Celery.
            #
            if should_run_in_background(
                query=query,
            ):
                task = run_raw_query_background.delay(
                    str(datasource.id),
                    data["sql"],
                    data["page"],
                    data["page_size"],
                )

                return Response(
                    {
                        "status": "queued",
                        "task_id": task.id,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            #
            # Lightweight raw query -> execute immediately.
            #
            result = execute_query(
                datasource=datasource,
                query=query,
            )

        except QueryValidationError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except QueryExecutionError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class QueryTaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        task_id,
    ):
        task = AsyncResult(
            task_id
        )

        if task.state == "PENDING":
            return Response(
                {
                    "status": "queued",
                    "task_id": task_id,
                }
            )

        if task.state == "STARTED":
            return Response(
                {
                    "status": "running",
                    "task_id": task_id,
                }
            )

        if task.state == "SUCCESS":
            return Response(
                {
                    "status": "completed",
                    "task_id": task_id,
                    "result": task.result,
                }
            )

        if task.state == "FAILURE":
            return Response(
                {
                    "status": "failed",
                    "task_id": task_id,
                    "error": str(
                        task.result
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": task.state.lower(),
                "task_id": task_id,
            }
        )