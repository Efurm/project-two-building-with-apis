from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("", views.library_index, name="index"),
    path("entries/<int:pk>/", views.entry_detail, name="entry_detail"),
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/status/", views.entry_status, name="entry_status"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
]
