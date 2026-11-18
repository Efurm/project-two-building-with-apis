import datetime
import io

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from catalog import tmdb
from catalog.models import Genre, Movie
from catalog.services import refresh_movie
from library.models import Entry

NEW_DETAILS = {
    "id": 27205,
    "title": "Inception (Remastered)",
    "original_title": "Inception",
    "release_date": "2010-07-16",
    "overview": "Updated overview.",
    "runtime": 150,
    "vote_average": 8.5,
    "poster_path": "/new-poster.jpg",
    "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}],
}


@pytest.mark.django_db
def test_refresh_replaces_details_and_genres_and_advances_last_fetched(make_movie, monkeypatch):
    stale_time = timezone.now() - datetime.timedelta(days=200)
    movie = make_movie(
        tmdb_id=27205,
        title="Inception",
        overview="Old overview.",
        runtime=148,
        vote_average=8.1,
        poster_path="/old-poster.jpg",
        last_fetched_at=stale_time,
    )
    movie.genres.set(
        [
            Genre.objects.create(tmdb_id=28, name="Action"),
            Genre.objects.create(tmdb_id=18, name="Drama"),
        ]
    )
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: NEW_DETAILS)

    refresh_movie(movie)

    movie.refresh_from_db()
    assert movie.title == "Inception (Remastered)"
    assert movie.release_date == datetime.date(2010, 7, 16)
    assert movie.overview == "Updated overview."
    assert movie.runtime == 150
    assert movie.vote_average == pytest.approx(8.5)
    assert movie.poster_path == "/new-poster.jpg"
    assert sorted(movie.genres.values_list("name", flat=True)) == ["Action", "Science Fiction"]
    assert movie.last_fetched_at > stale_time + datetime.timedelta(days=199)


def test_failed_refresh_from_entry_page_keeps_stored_movie_and_shows_alert(
    owner_client, owner, make_movie, monkeypatch
):
    fetched_at = timezone.now() - datetime.timedelta(days=30)
    movie = make_movie(
        tmdb_id=27205,
        title="Inception",
        runtime=148,
        poster_path="/old.jpg",
        last_fetched_at=fetched_at,
    )
    movie.genres.set([Genre.objects.create(tmdb_id=28, name="Action")])
    Entry.objects.create(user=owner, movie=movie)

    def tmdb_down(tmdb_id):
        raise tmdb.TMDBError(
            "timeout", "TMDB did not respond within 10 seconds. Try again shortly."
        )

    monkeypatch.setattr(tmdb, "get_movie_details", tmdb_down)

    response = owner_client.post(reverse("catalog:refresh", args=[27205]), HTTP_HX_REQUEST="true")
    html = response.content.decode()

    assert response.status_code == 200
    assert 'role="alert"' in html
    assert "TMDB did not respond within 10 seconds. Try again shortly." in html
    assert "Inception" in html
    movie.refresh_from_db()
    assert (movie.title, movie.runtime, movie.poster_path) == ("Inception", 148, "/old.jpg")
    assert list(movie.genres.values_list("name", flat=True)) == ["Action"]
    assert movie.last_fetched_at == fetched_at


@pytest.mark.django_db
def test_refresh_movies_command_refreshes_only_movies_older_than_cutoff(make_movie, monkeypatch):
    now = timezone.now()
    make_movie(tmdb_id=1, title="Ancient", last_fetched_at=now - datetime.timedelta(days=400))
    make_movie(tmdb_id=2, title="Stale", last_fetched_at=now - datetime.timedelta(days=181))
    make_movie(tmdb_id=3, title="Recent", last_fetched_at=now - datetime.timedelta(days=179))
    make_movie(tmdb_id=4, title="Fresh", last_fetched_at=now - datetime.timedelta(days=2))
    monkeypatch.setattr(
        tmdb,
        "get_movie_details",
        lambda tmdb_id: {"id": tmdb_id, "title": f"Refreshed {tmdb_id}", "genres": []},
    )

    def titles():
        return dict(Movie.objects.values_list("tmdb_id", "title"))

    call_command("refresh_movies", stdout=io.StringIO())
    assert titles() == {1: "Refreshed 1", 2: "Refreshed 2", 3: "Recent", 4: "Fresh"}

    call_command("refresh_movies", "--older-than", "30", stdout=io.StringIO())
    assert titles() == {1: "Refreshed 1", 2: "Refreshed 2", 3: "Refreshed 3", 4: "Fresh"}


# --- Ordinary tests ---------------------------------------------------------------------


@pytest.fixture
def owned_movie(owner, make_movie):
    movie = make_movie(tmdb_id=27205, title="Inception")
    entry = Entry.objects.create(user=owner, movie=movie)
    return movie, entry


def refresh_url(tmdb_id=27205):
    return reverse("catalog:refresh", args=[tmdb_id])


def test_successful_htmx_refresh_returns_updated_details_with_success_status(
    owner_client, owned_movie, monkeypatch
):
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: NEW_DETAILS)

    html = owner_client.post(refresh_url(), HTTP_HX_REQUEST="true").content.decode()

    assert "<html" not in html
    assert 'id="movie-details"' in html
    assert "Updated from TMDB." in html
    assert "Inception (Remastered)" in html
    assert "150 min" in html
    assert 'role="alert"' not in html


def test_entry_page_has_refresh_button_targeting_details(owner_client, owned_movie):
    _, entry = owned_movie

    html = owner_client.get(reverse("library:entry_detail", args=[entry.pk])).content.decode()

    assert f'hx-post="{refresh_url()}"' in html
    assert 'hx-target="#movie-details"' in html
    assert "Refresh from TMDB" in html


@pytest.mark.parametrize(
    ("fails", "expected"),
    [(False, "Updated from TMDB."), (True, "Could not refresh from TMDB: TMDB is down.")],
)
def test_non_htmx_refresh_redirects_to_entry_page_with_message(
    owner_client, owned_movie, monkeypatch, fails, expected
):
    _, entry = owned_movie

    def details(tmdb_id):
        if fails:
            raise tmdb.TMDBError("connection", "TMDB is down.")
        return NEW_DETAILS

    monkeypatch.setattr(tmdb, "get_movie_details", details)

    response = owner_client.post(refresh_url(), follow=True)

    assert response.redirect_chain[-1][0] == reverse("library:entry_detail", args=[entry.pk])
    assert expected in response.content.decode()


def test_refresh_requires_sign_in(anon_client, owned_movie):
    response = anon_client.post(refresh_url())

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


def test_refresh_rejects_get(owner_client, owned_movie):
    assert owner_client.get(refresh_url()).status_code == 405


def test_refresh_of_movie_not_in_my_library_is_404(client, stranger, owned_movie, make_movie):
    make_movie(tmdb_id=603, title="Not in anyone's library")
    client.force_login(stranger)

    assert client.post(refresh_url(27205)).status_code == 404
    assert client.post(refresh_url(603)).status_code == 404


@pytest.mark.django_db
def test_command_continues_past_failures_and_reports_summary(make_movie, monkeypatch):
    old = timezone.now() - datetime.timedelta(days=365)
    make_movie(tmdb_id=1, title="Good One", last_fetched_at=old)
    make_movie(tmdb_id=2, title="Broken", last_fetched_at=old)
    make_movie(tmdb_id=3, title="Good Two", last_fetched_at=old)

    def details(tmdb_id):
        if tmdb_id == 2:
            raise tmdb.TMDBError("http", "TMDB returned HTTP 404.")
        return {"id": tmdb_id, "title": f"Refreshed {tmdb_id}", "genres": []}

    monkeypatch.setattr(tmdb, "get_movie_details", details)
    out, err = io.StringIO(), io.StringIO()

    call_command("refresh_movies", stdout=out, stderr=err)

    assert dict(Movie.objects.values_list("tmdb_id", "title")) == {
        1: "Refreshed 1",
        2: "Broken",
        3: "Refreshed 3",
    }
    assert Movie.objects.get(tmdb_id=2).last_fetched_at == old
    assert "3 movie(s) last fetched more than 180 day(s) ago." in out.getvalue()
    assert "Done: 2 refreshed, 1 failed." in out.getvalue()
    assert "Broken (TMDB id 2): TMDB returned HTTP 404." in err.getvalue()


@pytest.mark.django_db
def test_command_with_nothing_stale_reports_zero(make_movie):
    make_movie(tmdb_id=1)  # just fetched; TMDB is blocked so any call would fail the test
    out = io.StringIO()

    call_command("refresh_movies", stdout=out)

    assert "0 movie(s)" in out.getvalue()
    assert "Done: 0 refreshed, 0 failed." in out.getvalue()


@pytest.mark.django_db
def test_command_rejects_negative_days():
    with pytest.raises(CommandError):
        call_command("refresh_movies", "--older-than", "-1")
