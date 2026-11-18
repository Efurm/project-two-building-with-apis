from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from library import list_views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="library:index"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("find/", include("catalog.urls")),
    path("library/", include("library.urls")),
    path("lists/", include("library.list_urls")),
    path("u/<str:username>/", list_views.profile, name="profile"),
    path("shared/", list_views.shared_with_me, name="shared"),
    path("admin/", admin.site.urls),
]
