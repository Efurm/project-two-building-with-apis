import copy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from catalog.models import Genre, Movie
from library.models import Entry, MovieList


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


class UsernamesField(serializers.Field):
    """A many-to-many to User, read and written as a list of usernames.

    Every username must belong to an existing account; otherwise the whole request is
    rejected with one "No account has the username X." message per unknown name.
    """

    default_error_messages = {
        "not_a_list": "Expected a list of usernames.",
        "unknown": "No account has the username {username}.",
    }

    def to_representation(self, value):
        return sorted(user.username for user in value.all())

    def to_internal_value(self, data):
        if not isinstance(data, list) or not all(isinstance(name, str) for name in data):
            self.fail("not_a_list")
        names = list(dict.fromkeys(name.strip() for name in data))
        users = {u.username: u for u in get_user_model().objects.filter(username__in=names)}
        unknown = [name for name in names if name not in users]
        if unknown:
            raise serializers.ValidationError(
                [self.error_messages["unknown"].format(username=name) for name in unknown]
            )
        return [users[name] for name in names]


class MovieListSerializer(serializers.ModelSerializer):
    """A named list. `shared_with` is a list of usernames."""

    owner = serializers.CharField(source="owner.username", read_only=True)
    shared_with = UsernamesField(required=False)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = MovieList
        fields = [
            "id",
            "name",
            "owner",
            "visibility",
            "shared_with",
            "item_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def get_item_count(self, movie_list):
        return movie_list.items.count()

    def validate_shared_with(self, users):
        """Same rule as the website: the owner can't share a list with themselves."""
        request = self.context.get("request")
        if request is not None and any(user.pk == request.user.pk for user in users):
            raise serializers.ValidationError("You own this list, so you can always see it.")
        return users
