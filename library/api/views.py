from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from catalog import services, tmdb
from library.browse import browse_entries
from library.models import Entry, ListItem, MovieList

from .serializers import EntrySerializer, MovieListSerializer

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


class MovieListViewSet(viewsets.ModelViewSet):
    """Named lists, with the same visibility rules as the website.

    Reads (GET) go through `MovieList.objects.visible_to()`, so anonymous clients can
    read Public lists and hidden lists are 404. Writes only ever see the requester's
    own lists, so a non-owner's write is 404 even on a list they can read.

    Listing filters (both derived from `visible_to`): `shared_with_me=true` (lists other
    users share with you, like the "Shared with me" page) and `owner=<username>`.
    """

    serializer_class = MovieListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.method in permissions.SAFE_METHODS:
            lists = MovieList.objects.visible_to(self.request.user)
        else:
            lists = MovieList.objects.filter(owner=self.request.user)
        if self.action == "list":
            lists = self._filter_listing(lists)
        return lists.select_related("owner").prefetch_related("shared_with")

    def _filter_listing(self, lists):
        params = self.request.query_params
        if params.get("shared_with_me", "").lower() in ("true", "1", "yes"):
            if not self.request.user.is_authenticated:
                return lists.none()
            lists = lists.filter(visibility=MovieList.Visibility.SHARED).exclude(
                owner=self.request.user
            )
        owner = (params.get("owner") or "").strip()
        if owner:
            lists = lists.filter(owner__username=owner)
        return lists

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get", "post"])
    def items(self, request, pk=None):
        """GET: the list's entries (browse parameters, paginated). POST {"entry": id}: add."""
        movie_list = self.get_object()
        if request.method == "POST":
            return self._add_item(request, movie_list)
        entries = browse_entries(
            Entry.objects.filter(list_items__movie_list=movie_list)
            .select_related("movie")
            .prefetch_related("movie__genres"),
            request.query_params,
        )
        page = self.paginate_queryset(entries)
        return self.get_paginated_response(EntrySerializer(page, many=True).data)

    def _add_item(self, request, movie_list):
        """Add one of the requester's own entries (others' entries are 404).

        201 when added, 200 when it was already in the list.
        """
        try:
            entry_id = int(request.data.get("entry"))
        except (TypeError, ValueError):
            raise serializers.ValidationError(
                {"entry": ["A valid entry id is required."]}
            ) from None
        entry = get_object_or_404(
            Entry.objects.select_related("movie"), pk=entry_id, user=request.user
        )
        _, created = ListItem.objects.get_or_create(movie_list=movie_list, entry=entry)
        return Response(
            EntrySerializer(entry).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path=r"items/(?P<entry_pk>[0-9]+)")
    def remove_item(self, request, pk=None, entry_pk=None):
        """DELETE: remove an entry from the list (the entry stays in the library)."""
        movie_list = self.get_object()
        deleted, _ = ListItem.objects.filter(movie_list=movie_list, entry_id=entry_pk).delete()
        if not deleted:
            raise NotFound("That entry is not in this list.")
        return Response(status=status.HTTP_204_NO_CONTENT)
