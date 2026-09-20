from django.urls import path

from .views import RunQueryView

urlpatterns = [
    path("run/", RunQueryView.as_view(), name="run-query"),
]
