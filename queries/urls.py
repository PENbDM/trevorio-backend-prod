from django.urls import path

from .views import (
    RunQueryView,
    RunRawQueryView,
    QueryTaskStatusView,
)


urlpatterns = [
    path(
        "run/",
        RunQueryView.as_view(),
        name="run-query",
    ),

    path("run/latest/", RunQueryView.as_view(mode="latest"), name="run-latest"),

    path(
        "run/raw/",
        RunRawQueryView.as_view(),
        name="run-raw-query",
    ),

    path(
        "tasks/<str:task_id>/",
        QueryTaskStatusView.as_view(),
        name="query-task-status",
    ),
]