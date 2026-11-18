from django.urls import reverse

from catalog import tmdb
from library.models import Entry


def tmdb_down(*args, **kwargs):
    raise tmdb.TMDBError("connection", "Could not connect to TMDB.")


def test_saving_a_locally_stored_movie_works_while_tmdb_is_down(
    owner_client, owner, make_movie, monkeypatch
):
    movie = make_movie(tmdb_id=27205, title="Inception")
    monkeypatch.setattr(tmdb, "get_movie_details", tmdb_down)
    monkeypatch.setattr(tmdb, "search_movies", tmdb_down)

    response = owner_client.post(
        reverse("catalog:save", args=[27205]), {"status": "watched"}, HTTP_HX_REQUEST="true"
    )

    assert response.status_code == 200
    entry = Entry.objects.filter(user=owner, movie=movie).first()
    assert entry is not None
    assert entry.status == Entry.Status.WATCHED
    assert "In library ✓" in response.content.decode()


def test_saving_the_same_movie_twice_keeps_one_entry_and_shows_in_library(
    owner_client, owner, make_movie
):
    make_movie(tmdb_id=27205, title="Inception")
    save_url = reverse("catalog:save", args=[27205])
    owner_client.raise_request_exception = False  # observe the response a browser would get

    owner_client.post(save_url, {"status": "want_to_watch"}, HTTP_HX_REQUEST="true")
    response = owner_client.post(save_url, {"status": "watched"}, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert Entry.objects.filter(user=owner, movie__tmdb_id=27205).count() == 1
    assert Entry.objects.get(user=owner, movie__tmdb_id=27205).status == Entry.Status.WANT_TO_WATCH
    assert "In library ✓" in response.content.decode()


def test_saving_an_unstored_movie_fetches_details_and_defaults_to_want_to_watch(
    owner_client, owner, monkeypatch
):
    details = {"id": 603, "title": "The Matrix", "release_date": "1999-03-31", "genres": []}
    monkeypatch.setattr(tmdb, "get_movie_details", lambda tmdb_id: details)

    response = owner_client.post(reverse("catalog:save", args=[603]), HTTP_HX_REQUEST="true")

    entry = Entry.objects.get(user=owner)
    assert entry.movie.title == "The Matrix"
    assert entry.status == Entry.Status.WANT_TO_WATCH
    assert "In library ✓" in response.content.decode()


def test_unknown_status_falls_back_to_want_to_watch(owner_client, owner, make_movie):
    make_movie(tmdb_id=27205)

    owner_client.post(
        reverse("catalog:save", args=[27205]), {"status": "watching"}, HTTP_HX_REQUEST="true"
    )

    assert Entry.objects.get(user=owner).status == Entry.Status.WANT_TO_WATCH


def test_saving_unstored_movie_while_tmdb_down_shows_alert_and_keeps_save_button(
    owner_client, monkeypatch
):
    monkeypatch.setattr(tmdb, "get_movie_details", tmdb_down)

    response = owner_client.post(
        reverse("catalog:save", args=[27205]), {"status": "watched"}, HTTP_HX_REQUEST="true"
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert not Entry.objects.exists()
    assert 'role="alert"' in content
    assert "Could not connect to TMDB." in content
    assert "In library ✓" not in content
    assert ">Save</button>" in content


def test_save_requires_sign_in(anon_client, make_movie):
    make_movie(tmdb_id=27205)

    response = anon_client.post(reverse("catalog:save", args=[27205]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))
    assert not Entry.objects.exists()


def test_save_rejects_get(owner_client):
    assert owner_client.get(reverse("catalog:save", args=[27205])).status_code == 405


def test_non_htmx_save_redirects_to_library(owner_client, owner, make_movie):
    make_movie(tmdb_id=27205)

    response = owner_client.post(reverse("catalog:save", args=[27205]), {"status": "watched"})

    assert response.status_code == 302
    assert response["Location"] == reverse("library:index")
    assert Entry.objects.filter(user=owner).count() == 1


def test_another_users_entry_does_not_block_saving(owner_client, owner, stranger, make_movie):
    movie = make_movie(tmdb_id=27205)
    Entry.objects.create(user=stranger, movie=movie)

    owner_client.post(reverse("catalog:save", args=[27205]), HTTP_HX_REQUEST="true")

    assert Entry.objects.filter(movie=movie).count() == 2
    assert Entry.objects.filter(user=owner, movie=movie).exists()
