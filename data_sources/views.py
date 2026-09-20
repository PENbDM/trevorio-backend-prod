from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import accessible_datasources, user_can_admin, user_is_owner
from .models import DataSource
from .serializers import DataSourceSchemaSerializer, DataSourceSerializer
from .services.postgres import DatabaseConnectionError
from .services.schema_sync import sync_datasource_schema


class DatasourceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        return (
            accessible_datasources(self.request.user)
            .prefetch_related("memberships")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        datasource = serializer.save()
        try:
            sync_datasource_schema(datasource)
        except DatabaseConnectionError:
            # The connection itself was already validated by the serializer.
            # Keep the datasource so the user can retry schema sync from the workspace.
            pass


class DatasourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        return accessible_datasources(self.request.user).prefetch_related("memberships")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not user_is_owner(request.user, instance):
            return Response(
                {"detail": "Only the owner can update connection credentials."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not user_is_owner(request.user, instance):
            return Response(
                {"detail": "Only the owner can delete this datasource."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DatasourceSchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        datasource = get_object_or_404(
            accessible_datasources(request.user).prefetch_related("tables__columns"),
            pk=pk,
        )
        return Response(DataSourceSchemaSerializer(datasource).data)


class DatasourceSyncSchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        datasource = get_object_or_404(
            accessible_datasources(request.user),
            pk=pk,
        )
        if not user_can_admin(request.user, datasource):
            return Response(
                {"detail": "Only the owner or an admin can sync the schema."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            sync_datasource_schema(datasource)
        except DatabaseConnectionError as exc:
            DataSource.objects.filter(pk=datasource.pk).update(status="error")
            return Response(
                {"connection": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        datasource.refresh_from_db()
        datasource = DataSource.objects.prefetch_related("tables__columns").get(
            pk=datasource.pk
        )
        return Response(DataSourceSchemaSerializer(datasource).data)
