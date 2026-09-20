
from django.urls import path

from .views import (
    GithubConnectionStatusView,
    GithubConnectView,
    GithubCallbackView,
    GithubRepositoriesView,
    GithubFilesView,
    GithubContentView,
)

urlpatterns = [
    path(
        "github/status/",
        GithubConnectionStatusView.as_view(),
    ),
    path(
        "github/connect/",
        GithubConnectView.as_view(),
    ),
    path(
        "github/callback/",
        GithubCallbackView.as_view(),
    ),
    path(
        "github/repos/",
        GithubRepositoriesView.as_view(),
    ),
    path(
        "github/files/",
        GithubFilesView.as_view(),
    ),
    path(
        "github/content/",
        GithubContentView.as_view(),
    ),
]