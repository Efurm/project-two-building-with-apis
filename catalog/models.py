from django.db import models

from . import tmdb


class Genre(models.Model):
    """A TMDB genre."""

    tmdb_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    """A movie's TMDB details copied locally. Shared by all users, one row per TMDB id."""

    tmdb_id = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=300)
    original_title = models.CharField(max_length=300, blank=True)
    release_date = models.DateField(null=True, blank=True)
    overview = models.TextField(blank=True)
    runtime = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Minutes")
    vote_average = models.FloatField(default=0)
    # Nullable per the PRD: mirrors TMDB's null poster_path ("no poster").
    poster_path = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001
    genres = models.ManyToManyField(Genre, blank=True, related_name="movies")
    last_fetched_at = models.DateTimeField()

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title

    @property
    def year(self):
        return self.release_date.year if self.release_date else None

    @property
    def poster_url(self):
        return tmdb.poster_url(self.poster_path)
