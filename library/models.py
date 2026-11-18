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


class MovieListQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Lists `user` may view: the single source of truth for list visibility.

        Owners see all their lists; anyone (including anonymous visitors) sees Public
        lists; Shared lists are visible to the users in `shared_with`. `shared_with`
        only counts while the list is Shared. Writing is always owner-only.
        """
        public = models.Q(visibility=MovieList.Visibility.PUBLIC)
        if not user.is_authenticated:
            return self.filter(public)
        # A subquery (not a join) so a list never appears twice.
        shared_with_user = MovieList.shared_with.through.objects.filter(user=user).values(
            "movielist_id"
        )
        return self.filter(
            models.Q(owner=user)
            | public
            | models.Q(visibility=MovieList.Visibility.SHARED, pk__in=shared_with_user)
        )


class MovieList(models.Model):
    """A user's named list of their own library entries."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"
        SHARED = "shared", "Shared"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="movie_lists"
    )
    name = models.CharField(max_length=100)
    visibility = models.CharField(max_length=10, choices=Visibility, default=Visibility.PRIVATE)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_lists"
    )
    entries = models.ManyToManyField(Entry, through="ListItem", related_name="movie_lists")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MovieListQuerySet.as_manager()

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class ListItem(models.Model):
    """One entry's membership in one list. Deleting either side removes only this row."""

    movie_list = models.ForeignKey(MovieList, on_delete=models.CASCADE, related_name="items")
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="list_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["movie_list", "entry"], name="unique_entry_per_list"),
        ]

    def __str__(self):
        return f"{self.entry.movie} in {self.movie_list}"
