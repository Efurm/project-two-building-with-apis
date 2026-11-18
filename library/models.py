from django.conf import settings
from django.core.exceptions import ValidationError
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The status as last loaded or saved, so clean() can tell "changed away from
        # Watched" (clear the watched-only fields) from "never Watched" (reject them).
        self._saved_status = self.status

    def __str__(self):
        return f"{self.user} – {self.movie}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._saved_status = self.status

    def clear_watched_fields(self):
        self.rating = None
        self.date_watched = None
        self.times_watched = 0

    def clean(self):
        """Rating, date watched, and times watched > 0 are allowed only when Watched.

        Changing status away from Watched clears those fields instead of rejecting them.
        """
        super().clean()
        if self.status == self.Status.WATCHED:
            return
        if self._saved_status == self.Status.WATCHED:
            self.clear_watched_fields()
            return
        errors = {}
        if self.rating is not None:
            errors["rating"] = "You can rate a movie only after marking it Watched."
        if self.date_watched is not None:
            errors["date_watched"] = "Set a date watched only when the movie is marked Watched."
        if self.times_watched:
            errors["times_watched"] = "Times watched must be 0 unless the movie is marked Watched."
        if errors:
            raise ValidationError(errors)
