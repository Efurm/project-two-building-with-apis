from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="library:index"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("find/", include("catalog.urls")),
    path("library/", include("library.urls")),
    path("admin/", admin.site.urls),
]
