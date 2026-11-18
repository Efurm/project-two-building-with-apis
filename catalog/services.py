"""Shared catalog services used by both the website and the API."""

import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import tmdb
from .models import Genre, Movie


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _store_details(movie, data):
    """Copy TMDB movie-details JSON onto `movie`, save it, and set its genres."""
    movie.title = data.get("title") or "(untitled)"
    movie.original_title = data.get("original_title") or ""
    movie.release_date = _parse_date(data.get("release_date"))
    movie.overview = data.get("overview") or ""
    movie.runtime = data.get("runtime") or None
    movie.vote_average = data.get("vote_average") or 0
    movie.poster_path = data.get("poster_path") or None
    movie.last_fetched_at = timezone.now()
    movie.save()

    genres = []
    for item in data.get("genres") or []:
        genre, _ = Genre.objects.update_or_create(
            tmdb_id=item["id"], defaults={"name": item.get("name", "")}
        )
        genres.append(genre)
    movie.genres.set(genres)
    return movie


def get_or_fetch_movie(tmdb_id):
    """Return the stored Movie for `tmdb_id`, fetching and storing it from TMDB if needed.

    Raises `tmdb.TMDBError` only when the movie is not stored and TMDB fails.
    """
    existing = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if existing:
        return existing

    data = tmdb.get_movie_details(tmdb_id)
    try:
        with transaction.atomic():
            return _store_details(Movie(tmdb_id=tmdb_id), data)
    except IntegrityError:
        # Another request stored the same movie first.
        return Movie.objects.get(tmdb_id=tmdb_id)


def refresh_movie(movie):
    """Re-fetch `movie` from TMDB and update its stored details, genres, and last-fetched time.

    TMDB is called before anything is changed, so if it raises `tmdb.TMDBError` the stored
    movie is left exactly as it was.
    """
    data = tmdb.get_movie_details(movie.tmdb_id)
    with transaction.atomic():
        return _store_details(movie, data)
