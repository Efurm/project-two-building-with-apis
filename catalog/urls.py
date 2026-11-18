from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.find_movies, name="find"),
    path("save/<int:tmdb_id>/", views.save_movie, name="save"),
    path("refresh/<int:tmdb_id>/", views.refresh_movie, name="refresh"),
]
