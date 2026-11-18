import datetime
import re

import pytest
from django.urls import reverse

from catalog.models import Genre
from library.models import Entry


@pytest.fixture
def add_entry(owner, make_movie):
    """Create an entry for `owner` with a new movie; extra kwargs split between movie and entry."""
    counter = iter(range(1000, 2000))
    movie_fields = {"release_date", "genres"}

    def _add(title, **kwargs):
        genres = kwargs.pop("genres", [])
        movie_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in movie_fields}
        movie = make_movie(tmdb_id=next(counter), title=title, **movie_kwargs)
        movie.genres.set(genres)
        return Entry.objects.create(user=owner, movie=movie, **kwargs)

    return _add


def browse(client, **params):
    response = client.get(reverse("library:index"), params)
    assert response.status_code == 200
    return [entry.movie.title for entry in response.context["entries"]]


def test_search_matches_title_or_own_notes_case_insensitively(
    owner_client, add_entry, stranger, make_movie
):
    add_entry("The Dark Knight")
    add_entry("Heat", notes="A great DARK and moody crime film.")
    add_entry("Paddington", notes="Wholesome and bright.")
    Entry.objects.create(
        user=stranger, movie=make_movie(tmdb_id=1, title="Dark City"), notes="dark"
    )

    assert sorted(browse(owner_client, q="dark")) == ["Heat", "The Dark Knight"]


def test_status_genre_min_rating_and_decade_filters_each_narrow_and_combine(
    owner_client, add_entry
):
    scifi = Genre.objects.create(tmdb_id=878, name="Science Fiction")
    comedy = Genre.objects.create(tmdb_id=35, name="Comedy")
    watched = Entry.Status.WATCHED

    def date(year):
        return datetime.date(year, 6, 1)

    add_entry("Alien", genres=[scifi], release_date=date(1979), status=watched, rating=5)
    add_entry("Blade Runner", genres=[scifi], release_date=date(1982), status=watched, rating=4)
    add_entry("Brazil", genres=[scifi], release_date=date(1985), status=watched, rating=3)
    add_entry(
        "Back to the Future", genres=[comedy], release_date=date(1985), status=watched, rating=5
    )
    add_entry("Akira", genres=[scifi], release_date=datetime.date(1989, 12, 31))
    add_entry("Dune", genres=[scifi], release_date=date(1984), status=watched)
    add_entry(
        "Total Recall",
        genres=[scifi],
        release_date=datetime.date(1990, 1, 1),
        status=watched,
        rating=4,
    )
    add_entry("No Date", genres=[scifi], status=watched, rating=5)

    assert sorted(browse(owner_client, status="want_to_watch")) == ["Akira"]
    assert sorted(browse(owner_client, genre="35")) == ["Back to the Future"]
    assert sorted(browse(owner_client, min_rating="4")) == [
        "Alien",
        "Back to the Future",
        "Blade Runner",
        "No Date",
        "Total Recall",
    ]
    assert sorted(browse(owner_client, decade="1980")) == [
        "Akira",
        "Back to the Future",
        "Blade Runner",
        "Brazil",
        "Dune",
    ]
    assert browse(owner_client, status="watched", genre="878", min_rating="4", decade="1980") == [
        "Blade Runner"
    ]


@pytest.mark.parametrize(
    ("direction", "rated_order"),
    [("desc", ["Five", "Three", "One"]), ("asc", ["One", "Three", "Five"])],
)
def test_rating_sort_puts_unrated_last_in_both_directions(
    owner_client, add_entry, direction, rated_order
):
    watched = Entry.Status.WATCHED
    add_entry("Unrated A", status=watched)
    add_entry("Three", status=watched, rating=3)
    add_entry("Unrated B")
    add_entry("Five", status=watched, rating=5)
    add_entry("One", status=watched, rating=1)

    titles = browse(owner_client, sort="rating", dir=direction)

    assert titles[:3] == rated_order
    assert sorted(titles[3:]) == ["Unrated A", "Unrated B"]


# --- Ordinary tests ---------------------------------------------------------------------


def test_default_order_is_newest_added_first(owner_client, add_entry):
    add_entry("First")
    add_entry("Second")
    add_entry("Third")

    assert browse(owner_client) == ["Third", "Second", "First"]
    assert browse(owner_client, sort="added", dir="asc") == ["First", "Second", "Third"]


def test_title_sort_is_case_insensitive_and_defaults_to_ascending(owner_client, add_entry):
    add_entry("banana")
    add_entry("Apple")
    add_entry("cherry")

    assert browse(owner_client, sort="title") == ["Apple", "banana", "cherry"]
    assert browse(owner_client, sort="title", dir="desc") == ["cherry", "banana", "Apple"]


def test_release_date_sort_puts_undated_last(owner_client, add_entry):
    add_entry("Old", release_date=datetime.date(1950, 1, 1))
    add_entry("Undated")
    add_entry("New", release_date=datetime.date(2020, 1, 1))

    assert browse(owner_client, sort="released") == ["New", "Old", "Undated"]
    assert browse(owner_client, sort="released", dir="asc") == ["Old", "New", "Undated"]


def test_date_watched_sort_puts_unwatched_last(owner_client, add_entry):
    watched = Entry.Status.WATCHED
    add_entry("Early", status=watched, date_watched=datetime.date(2026, 1, 1))
    add_entry("Never")
    add_entry("Late", status=watched, date_watched=datetime.date(2026, 6, 1))

    assert browse(owner_client, sort="watched") == ["Late", "Early", "Never"]
    assert browse(owner_client, sort="watched", dir="asc") == ["Early", "Late", "Never"]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "dropped"},
        {"genre": "abc"},
        {"min_rating": "9"},
        {"min_rating": "0"},
        {"decade": "1985"},
        {"decade": "nineties"},
        {"sort": "popularity"},
        {"dir": "sideways"},
        {"page": "999"},
        {"page": "x"},
    ],
)
def test_invalid_parameters_are_ignored_not_errors(owner_client, add_entry, params):
    add_entry("Only Movie")

    assert browse(owner_client, **params) == ["Only Movie"]


def test_pages_hold_twenty_entries(owner_client, add_entry):
    for n in range(45):
        add_entry(f"Movie {n:02d}")

    page_one = browse(owner_client)
    page_three = browse(owner_client, page="3")

    assert len(page_one) == 20
    assert page_one[0] == "Movie 44"
    assert page_three == [f"Movie {n:02d}" for n in range(4, -1, -1)]


def test_pagination_links_keep_filters_and_sort(owner_client, add_entry):
    for n in range(25):
        add_entry(f"Dark {n:02d}")

    html = owner_client.get(
        reverse("library:index"), {"q": "dark", "sort": "title", "page": "1"}
    ).content.decode()

    assert 'href="/library/?q=dark&amp;sort=title&amp;page=2"' in html
    assert "Page 1 of 2" in html


def test_htmx_request_returns_browse_partial_and_full_request_returns_page(owner_client, add_entry):
    add_entry("Heat")

    partial = owner_client.get(
        reverse("library:index"), {"q": "heat"}, HTTP_HX_REQUEST="true"
    ).content.decode()
    full = owner_client.get(reverse("library:index"), {"q": "heat"}).content.decode()

    assert "<html" not in partial and 'data-testid="browse-form"' in partial
    assert "<html" in full and 'id="library-browse"' in full


def test_htmx_history_restore_gets_full_page(owner_client, add_entry):
    add_entry("Heat")

    html = owner_client.get(
        reverse("library:index"),
        HTTP_HX_REQUEST="true",
        HTTP_HX_HISTORY_RESTORE_REQUEST="true",
    ).content.decode()

    assert "<html" in html


def test_browse_form_pushes_url_and_targets_browse_area(owner_client, add_entry):
    add_entry("Heat")

    html = owner_client.get(reverse("library:index")).content.decode()

    assert 'hx-get="/library/"' in html
    assert 'hx-target="#library-browse"' in html
    assert 'hx-push-url="true"' in html


def test_controls_reflect_current_parameters(owner_client, add_entry):
    scifi = Genre.objects.create(tmdb_id=878, name="Science Fiction")
    add_entry("Alien", genres=[scifi], release_date=datetime.date(1979, 5, 25))

    html = owner_client.get(
        reverse("library:index"),
        {
            "q": "ali",
            "status": "want_to_watch",
            "genre": "878",
            "decade": "1970",
            "min_rating": "",
            "sort": "title",
            "dir": "desc",
        },
    ).content.decode()

    assert 'value="ali"' in html
    assert re.search(r'value="want_to_watch"\s+selected', html)
    assert re.search(r'value="878"\s+selected', html)
    assert re.search(r'value="1970"\s+selected', html)
    assert re.search(r'value="title"\s+selected', html)
    assert re.search(r'value="desc"\s+selected', html)


def test_filter_options_list_only_genres_and_decades_in_my_library(
    owner_client, add_entry, stranger, make_movie
):
    scifi = Genre.objects.create(tmdb_id=878, name="Science Fiction")
    western = Genre.objects.create(tmdb_id=37, name="Western")
    add_entry("Alien", genres=[scifi], release_date=datetime.date(1979, 5, 25))
    theirs = make_movie(tmdb_id=1, title="Unforgiven", release_date=datetime.date(1992, 8, 7))
    theirs.genres.set([western])
    Entry.objects.create(user=stranger, movie=theirs)

    html = owner_client.get(reverse("library:index")).content.decode()

    assert ">Science Fiction<" in html and ">Western<" not in html
    assert ">1970s<" in html and ">1990s<" not in html


def test_no_matches_shows_message_and_result_count(owner_client, add_entry):
    add_entry("Heat")

    html = owner_client.get(reverse("library:index"), {"q": "zzz"}).content.decode()

    assert "No movies match these filters." in html
    assert re.search(r'data-testid="result-count">\s*0 movies', html)


def test_empty_library_shows_empty_state_without_controls(owner_client):
    html = owner_client.get(reverse("library:index")).content.decode()

    assert "Your library is empty" in html
    assert 'data-testid="browse-form"' not in html
