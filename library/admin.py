from django.contrib import admin

from .models import Entry, ListItem, MovieList


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["movie", "user", "status", "rating", "created_at"]
    list_filter = ["status"]
    search_fields = ["movie__title", "user__username", "notes"]
    raw_id_fields = ["movie", "user"]


class ListItemInline(admin.TabularInline):
    model = ListItem
    raw_id_fields = ["entry"]
    extra = 0


@admin.register(MovieList)
class MovieListAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name", "owner__username"]
    raw_id_fields = ["owner"]
    inlines = [ListItemInline]
