from django.db import IntegrityError, transaction
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import APIException

from catalog import services, tmdb
from library.browse import browse_entries
from library.models import Entry

from .serializers import EntrySerializer

ALREADY_IN_LIBRARY = "This movie is already in your library."


class ProviderUnavailable(APIException):
    """TMDB was needed (the movie is not stored yet) and the request to it failed."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The movie database is unavailable. Try again later."
    default_code = "provider_unavailable"


class EntryViewSet(viewsets.ModelViewSet):
    """The requesting user's library entries (always private to their owner).

    Every action starts from the user's own entries, so other users' entries are 404.
    Listing accepts the website's browse parameters (q, status, genre, min_rating,
    decade, sort, dir, page) and returns 20 per page.
    """

    serializer_class = EntrySerializer

    def get_queryset(self):
        entries = (
            Entry.objects.filter(user=self.request.user)
            .select_related("movie")
            .prefetch_related("movie__genres")
        )
        if self.action == "list":
            entries = browse_entries(entries, self.request.query_params)
        return entries

    def perform_create(self, serializer):
        """Create an entry from a TMDB id via the shared get-or-fetch service.

        Rejects a movie already in the library (400) before contacting TMDB, and
        responds 503 with the client's readable message when TMDB is needed and fails.
        """
        tmdb_id = serializer.validated_data.pop("tmdb_id")
        if Entry.objects.filter(user=self.request.user, movie__tmdb_id=tmdb_id).exists():
            raise serializers.ValidationError({"tmdb_id": [ALREADY_IN_LIBRARY]})
        try:
            movie = services.get_or_fetch_movie(tmdb_id)
        except tmdb.TMDBError as error:
            raise ProviderUnavailable(detail=error.message) from error
        try:
            with transaction.atomic():
                serializer.save(user=self.request.user, movie=movie)
        except IntegrityError as error:  # a concurrent request saved it first
            raise serializers.ValidationError({"tmdb_id": [ALREADY_IN_LIBRARY]}) from error
