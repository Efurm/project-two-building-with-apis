from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from catalog.models import Movie


class Entry(models.Model):
    """One user's copy of one movie in their library."""

    class Status(models.TextChoices):
        WANT_TO_WATCH = "want_to_watch", "Want to watch"
        WATCHING = "watching", "Watching"
        WATCHED = "watched", "Watched"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries"
    )
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT, related_name="entries")
    status = models.CharField(max_length=20, choices=Status, default=Status.WANT_TO_WATCH)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    notes = models.TextField(blank=True)
    date_watched = models.DateField(null=True, blank=True)
    times_watched = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "entries"
        constraints = [
            models.UniqueConstraint(fields=["user", "movie"], name="unique_entry_per_user_movie"),
        ]

    def __str__(self):
        return f"{self.user} – {self.movie}"
