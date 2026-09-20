from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Current frontend compatibility: both prefixes point at the same auth views.
    path("api/auth/", include("accounts.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/datasources/", include("data_sources.urls")),
    path("api/queries/", include("queries.urls")),
]
