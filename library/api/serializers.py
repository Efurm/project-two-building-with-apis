import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from catalog.models import Genre, Movie
from library.models import Entry


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["tmdb_id", "name"]


class MovieSerializer(serializers.ModelSerializer):
    """Stored TMDB details (read-only; local data)."""

    genres = GenreSerializer(many=True, read_only=True)
    poster_url = serializers.CharField(read_only=True)

    class Meta:
        model = Movie
        fields = [
            "tmdb_id",
            "title",
            "original_title",
            "release_date",
            "overview",
            "runtime",
            "vote_average",
            "poster_path",
            "poster_url",
            "genres",
            "last_fetched_at",
        ]
        read_only_fields = fields


class EntrySerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    tmdb_id = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = Entry
        fields = [
            "id",
            "tmdb_id",
            "movie",
            "status",
            "rating",
            "notes",
            "date_watched",
            "times_watched",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "movie", "created_at", "updated_at"]

    def get_fields(self):
        """`tmdb_id` is only for creating; an entry's movie never changes afterwards."""
        fields = super().get_fields()
        if self.instance is not None:
            fields.pop("tmdb_id")
        return fields

    # Fields Entry.clean() may change (it clears them when status leaves Watched).
    WATCHED_ONLY_FIELDS = ("rating", "date_watched", "times_watched")

    def validate(self, attrs):
        """Apply the one cross-field rule defined on the model: `Entry.clean()`.

        Works on a copy so a rejected request leaves the instance untouched; any
        fields `clean()` clears are written back into the validated data.
        """
        candidate = copy.copy(self.instance) if self.instance else Entry()
        for field, value in attrs.items():
            if field != "tmdb_id":
                setattr(candidate, field, value)
        try:
            candidate.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        for field in self.WATCHED_ONLY_FIELDS:
            attrs[field] = getattr(candidate, field)
        return attrs
