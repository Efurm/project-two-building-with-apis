import datetime

import pytest

from catalog import tmdb
from catalog.models import Movie
from library.models import Entry


@pytest.fixture
def two_libraries(owner, stranger, make_movie):
    mine = [
        Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Heat")),
        Entry.objects.create(user=owner, movie=make_movie(tmdb_id=2, title="Ronin")),
    ]
    theirs = Entry.objects.create(user=stranger, movie=make_movie(tmdb_id=3, title="Theirs"))
    return mine, theirs


def test_token_request_lists_only_own_entries_and_others_are_404(
    api_client, owner, token_for, two_libraries
):
    mine, theirs = two_libraries
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token_for(owner)}")

    listing = api_client.get("/api/entries/")
    other = api_client.get(f"/api/entries/{theirs.pk}/")

    assert listing.status_code == 200
    assert sorted(item["id"] for item in listing.json()["results"]) == sorted(e.pk for e in mine)
    assert other.status_code == 404


def test_create_returns_503_with_detail_when_tmdb_is_needed_and_down(
    api_client, owner, monkeypatch
):
    def tmdb_down(tmdb_id):
        raise tmdb.TMDBError(
            "timeout", "TMDB did not respond within 10 seconds. Try again shortly."
        )

    monkeypatch.setattr(tmdb, "get_movie_details", tmdb_down)
    api_client.force_authenticate(owner)
    api_client.raise_request_exception = False  # observe the response a client would get

    response = api_client.post(
        "/api/entries/", {"tmdb_id": 27205, "status": "watched"}, format="json"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "TMDB did not respond within 10 seconds. Try again shortly."
    }
    assert not Entry.objects.exists()
    assert not Movie.objects.exists()


def test_api_updates_follow_the_same_entry_rules_as_the_website(api_client, owner, make_movie):
    api_client.force_authenticate(owner)
    unwatched = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Heat"))
    watched = Entry.objects.create(
        user=owner,
        movie=make_movie(tmdb_id=2, title="Ronin"),
        status=Entry.Status.WATCHED,
        rating=4,
        date_watched=datetime.date(2026, 11, 1),
        times_watched=2,
    )

    rejected = api_client.patch(f"/api/entries/{unwatched.pk}/", {"rating": 4}, format="json")

    assert rejected.status_code == 400
    assert rejected.json()["rating"] == ["You can rate a movie only after marking it Watched."]
    unwatched.refresh_from_db()
    assert unwatched.rating is None

    cleared = api_client.patch(f"/api/entries/{watched.pk}/", {"status": "watching"}, format="json")

    assert cleared.status_code == 200
    assert (cleared.json()["rating"], cleared.json()["date_watched"]) == (None, None)
    assert cleared.json()["times_watched"] == 0
    watched.refresh_from_db()
    assert watched.status == "watching"
    assert (watched.rating, watched.date_watched, watched.times_watched) == (None, None, 0)


# --- Ordinary tests ---------------------------------------------------------------------

DETAILS = {
    "id": 603,
    "title": "The Matrix",
    "release_date": "1999-03-31",
    "runtime": 136,
    "genres": [{"id": 878, "name": "Science Fiction"}],
}


@pytest.fixture
def owner_api(api_client, owner):
    api_client.force_authenticate(owner)
    return api_client


def test_anonymous_and_bad_token_requests_are_refused(api_client, two_libraries):
    anonymous = api_client.get("/api/entries/")
    assert anonymous.status_code == 401
    assert anonymous["WWW-Authenticate"] == "Token"

    api_client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
    assert api_client.get("/api/entries/").status_code == 401


def test_session_login_works_for_the_api(owner_client, two_libraries):
    response = owner_client.get("/api/entries/")

    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_list_includes_nested_movie_details(owner_api, owner, make_movie):
    from catalog.models import Genre

    movie = make_movie(tmdb_id=27205, title="Inception", poster_path="/p.jpg", runtime=148)
    movie.genres.add(Genre.objects.create(tmdb_id=878, name="Science Fiction"))
    Entry.objects.create(user=owner, movie=movie, notes="Dreams.")

    item = owner_api.get("/api/entries/").json()["results"][0]

    assert item["notes"] == "Dreams."
    assert item["movie"]["tmdb_id"] == 27205
    assert item["movie"]["title"] == "Inception"
    assert item["movie"]["runtime"] == 148
    assert item["movie"]["poster_url"] == "https://image.tmdb.org/t/p/w185/p.jpg"
    assert item["movie"]["genres"] == [{"tmdb_id": 878, "name": "Science Fiction"}]
    assert "tmdb_id" not in item  # write-only on the entry itself


def test_list_accepts_website_browse_parameters(owner_api, owner, make_movie):
    for n, title in enumerate(["Alpha", "Bravo", "Charlie"]):
        Entry.objects.create(
            user=owner,
            movie=make_movie(tmdb_id=n + 1, title=title),
            status=Entry.Status.WATCHED if title != "Bravo" else Entry.Status.WANT_TO_WATCH,
        )

    response = owner_api.get("/api/entries/", {"status": "watched", "sort": "title", "dir": "desc"})

    assert [i["movie"]["title"] for i in response.json()["results"]] == ["Charlie", "Alpha"]


def test_list_is_paginated_at_twenty(owner_api, owner, make_movie):
    for n in range(23):
        Entry.objects.create(user=owner, movie=make_movie(tmdb_id=n + 1, title=f"M{n:02d}"))

    first = owner_api.get("/api/entries/").json()
    second = owner_api.get("/api/entries/", {"page": 2}).json()

    assert first["count"] == 23 and len(first["results"]) == 20 and first["next"]
    assert len(second["results"]) == 3 and second["next"] is None


def test_create_fetches_unstored_movie_with_optional_fields(owner_api, owner, monkeypatch):
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: DETAILS)

    response = owner_api.post(
        "/api/entries/",
        {
            "tmdb_id": 603,
            "status": "watched",
            "rating": 5,
            "notes": "Whoa.",
            "date_watched": "2026-11-01",
            "times_watched": 3,
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movie"]["title"] == "The Matrix"
    assert (body["status"], body["rating"], body["times_watched"]) == ("watched", 5, 3)
    assert Entry.objects.get(user=owner).notes == "Whoa."


def test_create_with_only_tmdb_id_defaults_to_want_to_watch(owner_api, make_movie):
    make_movie(tmdb_id=603, title="The Matrix")  # stored: TMDB is never contacted

    response = owner_api.post("/api/entries/", {"tmdb_id": 603}, format="json")

    assert response.status_code == 201
    assert response.json()["status"] == "want_to_watch"
    assert response.json()["times_watched"] == 0


def test_create_for_stored_movie_works_while_tmdb_is_down(owner_api, make_movie, monkeypatch):
    make_movie(tmdb_id=603, title="The Matrix")

    def tmdb_down(tmdb_id):
        raise tmdb.TMDBError("connection", "Could not connect to TMDB.")

    monkeypatch.setattr(tmdb, "get_movie_details", tmdb_down)

    assert owner_api.post("/api/entries/", {"tmdb_id": 603}, format="json").status_code == 201


def test_create_duplicate_is_rejected_without_calling_tmdb(owner_api, owner, make_movie):
    Entry.objects.create(user=owner, movie=make_movie(tmdb_id=603, title="The Matrix"))

    response = owner_api.post("/api/entries/", {"tmdb_id": 603}, format="json")

    assert response.status_code == 400
    assert response.json() == {"tmdb_id": ["This movie is already in your library."]}
    assert Entry.objects.filter(user=owner).count() == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tmdb_id": "abc"},
        {"tmdb_id": 0},
        {"tmdb_id": 603, "status": "dropped"},
        {"tmdb_id": 603, "status": "watched", "rating": 6},
        {"tmdb_id": 603, "times_watched": -1},
        {"tmdb_id": 603, "rating": 3},
    ],
)
def test_create_rejects_invalid_input(owner_api, make_movie, payload):
    make_movie(tmdb_id=603, title="The Matrix")

    response = owner_api.post("/api/entries/", payload, format="json")

    assert response.status_code == 400
    assert not Entry.objects.exists()


def test_put_replaces_user_fields_and_ignores_tmdb_id(owner_api, owner, make_movie):
    entry = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Heat"))

    response = owner_api.put(
        f"/api/entries/{entry.pk}/",
        {"tmdb_id": 999, "status": "watched", "rating": 3, "notes": "", "times_watched": 1},
        format="json",
    )

    assert response.status_code == 200
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.times_watched) == ("watched", 3, 1)
    assert entry.movie.tmdb_id == 1


def test_delete_returns_204_and_removes_list_items(owner_api, owner, make_movie):
    from library.models import ListItem, MovieList

    entry = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Heat"))
    movie_list = MovieList.objects.create(owner=owner, name="Crime")
    ListItem.objects.create(movie_list=movie_list, entry=entry)

    response = owner_api.delete(f"/api/entries/{entry.pk}/")

    assert response.status_code == 204
    assert not Entry.objects.exists()
    assert not ListItem.objects.exists()
    assert MovieList.objects.filter(pk=movie_list.pk).exists()


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_other_users_entry_is_404_for_every_method(owner_api, two_libraries, method):
    _, theirs = two_libraries

    response = getattr(owner_api, method)(
        f"/api/entries/{theirs.pk}/", {"status": "watched"}, format="json"
    )

    assert response.status_code == 404
    theirs.refresh_from_db()
    assert theirs.status == Entry.Status.WANT_TO_WATCH
