from django.contrib import admin
from django.urls import include, path
from trevorio.health import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    # Current frontend compatibility: both prefixes point at the same auth views.
    path("api/auth/", include("accounts.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/datasources/", include("data_sources.urls")),
    path("api/queries/", include("queries.urls")),
    path("api/integrations/", include("integrations.urls"),
    ),
    path("api/streaming/", include("streaming.urls")),
    path('api/tracking/',include('tracking.urls')),
    path("health/", health_check, name="health-check"),
]
