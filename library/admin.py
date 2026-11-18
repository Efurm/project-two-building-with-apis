from django.contrib import admin

from .models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["movie", "user", "status", "rating", "created_at"]
    list_filter = ["status"]
    search_fields = ["movie__title", "user__username", "notes"]
    raw_id_fields = ["movie", "user"]
