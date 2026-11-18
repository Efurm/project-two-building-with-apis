from django.contrib import admin

from .models import Genre, Movie


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "tmdb_id"]
    search_fields = ["name"]


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "release_date", "tmdb_id", "last_fetched_at"]
    search_fields = ["title", "original_title"]
    list_filter = ["genres"]
