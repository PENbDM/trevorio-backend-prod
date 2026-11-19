from django.urls import path
from .views import stream_events

urlpatterns = [
    path('events/', stream_events),
]