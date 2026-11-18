import datetime

import pytest

from catalog import tmdb
from catalog.models import Movie
from catalog.services import get_or_fetch_movie

INCEPTION_DETAILS = {
    "id": 27205,
    "title": "Inception",
    "original_title": "Inception",
    "release_date": "2010-07-15",
    "overview": "Cobb, a skilled thief who commits corporate espionage…",
    "runtime": 148,
    "vote_average": 8.369,
    "poster_path": "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
    "genres": [
        {"id": 28, "name": "Action"},
        {"id": 878, "name": "Science Fiction"},
        {"id": 12, "name": "Adventure"},
    ],
}


@pytest.mark.django_db
def test_unstored_movie_is_fetched_from_tmdb_and_stored_with_genres(monkeypatch):
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: INCEPTION_DETAILS)

    get_or_fetch_movie(27205)

    assert Movie.objects.filter(tmdb_id=27205).exists()
    movie = Movie.objects.get(tmdb_id=27205)
    assert movie.title == "Inception"
    assert movie.original_title == "Inception"
    assert movie.release_date == datetime.date(2010, 7, 15)
    assert movie.overview.startswith("Cobb, a skilled thief")
    assert movie.runtime == 148
    assert movie.vote_average == pytest.approx(8.369)
    assert movie.poster_path == "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg"
    assert sorted(movie.genres.values_list("name", flat=True)) == [
        "Action",
        "Adventure",
        "Science Fiction",
    ]
    assert movie.last_fetched_at is not None


def test_stored_movie_is_returned_without_calling_tmdb(make_movie):
    # requests.get is blocked by the autouse fixture; any TMDB call would fail the test.
    stored = make_movie(tmdb_id=27205)

    assert get_or_fetch_movie(27205) == stored


@pytest.mark.django_db
def test_tmdb_failure_for_unstored_movie_raises_and_stores_nothing(monkeypatch):
    def failing(tmdb_id):
        raise tmdb.TMDBError("timeout", "TMDB did not respond.")

    monkeypatch.setattr(tmdb, "get_movie_details", failing)

    with pytest.raises(tmdb.TMDBError):
        get_or_fetch_movie(27205)
    assert not Movie.objects.exists()


@pytest.mark.django_db
def test_genres_are_shared_between_movies_not_duplicated(monkeypatch):
    other = dict(INCEPTION_DETAILS, id=157336, title="Interstellar")
    details = {27205: INCEPTION_DETAILS, 157336: other}
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: details[tmdb_id])

    get_or_fetch_movie(27205)
    get_or_fetch_movie(157336)

    from catalog.models import Genre

    assert Genre.objects.count() == 3
    assert Genre.objects.get(tmdb_id=878).movies.count() == 2


@pytest.mark.django_db
def test_missing_optional_details_are_stored_as_empty(monkeypatch):
    sparse = {"id": 1, "title": "Obscure", "release_date": "", "poster_path": None, "genres": []}
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: sparse)

    movie = get_or_fetch_movie(1)

    assert movie.release_date is None
    assert movie.poster_path is None
    assert movie.runtime is None
    assert movie.overview == ""
    assert movie.poster_url is None
    assert movie.year is None
