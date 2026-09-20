from django.urls import path

from .views import (
    DatasourceDetailView,
    DatasourceListCreateView,
    DatasourceSchemaView,
    DatasourceSyncSchemaView,
)

urlpatterns = [
    path("", DatasourceListCreateView.as_view(), name="datasource-list-create"),
    path("<uuid:pk>/", DatasourceDetailView.as_view(), name="datasource-detail"),
    path("<uuid:pk>/sync-schema/", DatasourceSyncSchemaView.as_view(), name="datasource-sync-schema"),
    path("<uuid:pk>/schema/", DatasourceSchemaView.as_view(), name="datasource-schema"),
]
