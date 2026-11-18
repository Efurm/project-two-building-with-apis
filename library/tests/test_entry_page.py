import datetime
import re

import pytest
from django.urls import reverse

from catalog.models import Genre
from library.models import Entry


@pytest.fixture
def entry(owner, make_movie):
    movie = make_movie(
        title="Inception",
        release_date=datetime.date(2010, 7, 15),
        runtime=148,
        vote_average=8.37,
        overview="A thief who steals corporate secrets.",
        poster_path="/abc.jpg",
    )
    movie.genres.add(Genre.objects.create(tmdb_id=878, name="Science Fiction"))
    return Entry.objects.create(user=owner, movie=movie, notes="Line one\nLine two")


@pytest.fixture
def watched_entry(entry):
    entry.status = Entry.Status.WATCHED
    entry.rating = 4
    entry.date_watched = datetime.date(2026, 11, 1)
    entry.times_watched = 2
    entry.save()
    return entry


def edit_url(entry):
    return reverse("library:entry_edit", args=[entry.pk])


def form_data(**overrides):
    data = {
        "status": "watched",
        "rating": "4",
        "date_watched": "2026-11-01",
        "times_watched": "2",
        "notes": "Great.",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def watched_only_inputs(html):
    return re.findall(r"<(?:input|button)[^>]*data-watched-only[^>]*>", html)


# --- Entry page -------------------------------------------------------------------------


def test_entry_page_shows_stored_movie_details_and_user_data(owner_client, entry):
    html = owner_client.get(reverse("library:entry_detail", args=[entry.pk])).content.decode()

    assert "Inception" in html and "(2010)" in html
    assert "148 min" in html
    assert "Science Fiction" in html
    assert "8.4/10" in html
    assert "A thief who steals corporate secrets." in html
    assert 'src="https://image.tmdb.org/t/p/w185/abc.jpg"' in html
    assert "Want to watch" in html
    assert 'data-testid="entry-panel"' in html


def test_notes_are_plain_text_escaped_with_line_breaks_kept(owner_client, entry):
    entry.notes = "<script>alert(1)</script>\nsecond line"
    entry.save()

    html = owner_client.get(reverse("library:entry_detail", args=[entry.pk])).content.decode()

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;\nsecond line" in html
    assert "whitespace-pre-line" in html


def test_entry_page_requires_sign_in(anon_client, entry):
    response = anon_client.get(reverse("library:entry_detail", args=[entry.pk]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


@pytest.mark.parametrize(
    ("method", "url_name"),
    [
        ("get", "library:entry_detail"),
        ("get", "library:entry_edit"),
        ("post", "library:entry_edit"),
        ("post", "library:entry_status"),
    ],
)
def test_other_users_entries_return_404(client, stranger, entry, method, url_name):
    client.force_login(stranger)

    response = getattr(client, method)(reverse(url_name, args=[entry.pk]), form_data())

    assert response.status_code == 404
    entry.refresh_from_db()
    assert entry.status == Entry.Status.WANT_TO_WATCH


def test_htmx_get_of_entry_page_returns_panel_partial(owner_client, entry):
    html = owner_client.get(
        reverse("library:entry_detail", args=[entry.pk]), HTTP_HX_REQUEST="true"
    ).content.decode()

    assert "<html" not in html
    assert 'data-testid="entry-panel"' in html


# --- Edit form --------------------------------------------------------------------------


def test_htmx_edit_returns_form_partial(owner_client, entry):
    html = owner_client.get(edit_url(entry), HTTP_HX_REQUEST="true").content.decode()

    assert "<html" not in html
    assert 'data-testid="entry-form"' in html
    assert f'hx-post="{edit_url(entry)}"' in html
    assert 'hx-target="#entry-panel"' in html


def test_non_htmx_edit_renders_full_page_with_form(owner_client, entry):
    html = owner_client.get(edit_url(entry)).content.decode()

    assert "<html" in html
    assert 'data-testid="entry-form"' in html
    assert "Science Fiction" in html


def test_watched_only_inputs_are_disabled_unless_watched(owner_client, entry, watched_entry):
    html = owner_client.get(edit_url(watched_entry), HTTP_HX_REQUEST="true").content.decode()
    inputs = watched_only_inputs(html)
    assert len(inputs) == 9  # 6 rating radios + clear button + date + times
    assert not any("disabled" in tag for tag in inputs)
    assert re.search(r'value="4"[^>]*checked', html)

    watched_entry.status = Entry.Status.WATCHING
    watched_entry.save()  # full_clean is not called here; values remain but status changed
    html = owner_client.get(edit_url(watched_entry), HTTP_HX_REQUEST="true").content.decode()
    assert all("disabled" in tag for tag in watched_only_inputs(html))


def test_valid_htmx_save_returns_updated_panel(owner_client, entry):
    response = owner_client.post(edit_url(entry), form_data(), HTTP_HX_REQUEST="true")
    html = response.content.decode()

    assert 'data-testid="entry-panel"' in html
    assert 'aria-label="4 out of 5 stars"' in html
    assert "Nov 1, 2026" in html
    assert "Great." in html
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.times_watched) == ("watched", 4, 2)
    assert entry.date_watched == datetime.date(2026, 11, 1)


def test_non_htmx_valid_save_redirects_to_entry_page(owner_client, entry):
    response = owner_client.post(edit_url(entry), form_data())

    assert response.status_code == 302
    assert response["Location"] == reverse("library:entry_detail", args=[entry.pk])


def test_non_htmx_invalid_save_renders_full_page_with_errors(owner_client, entry):
    response = owner_client.post(edit_url(entry), form_data(status="want_to_watch"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "<html" in html
    assert "You can rate a movie only after marking it Watched." in html


def test_disabled_inputs_missing_from_post_save_as_empty(owner_client, entry):
    response = owner_client.post(
        edit_url(entry),
        form_data(status="watching", rating=None, date_watched=None, times_watched=None),
        HTTP_HX_REQUEST="true",
    )

    assert 'data-testid="entry-panel"' in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == "watching"
    assert (entry.rating, entry.date_watched, entry.times_watched) == (None, None, 0)


def test_clearing_the_rating_leaves_watched_entry_unrated(owner_client, watched_entry):
    owner_client.post(edit_url(watched_entry), form_data(rating=""), HTTP_HX_REQUEST="true")

    watched_entry.refresh_from_db()
    assert watched_entry.rating is None
    assert watched_entry.status == "watched"


@pytest.mark.parametrize(
    ("field", "value"),
    [("rating", "6"), ("rating", "0"), ("rating", "four"), ("times_watched", "-1")],
)
def test_out_of_range_values_are_rejected(owner_client, entry, field, value):
    response = owner_client.post(
        edit_url(entry), form_data(**{field: value}), HTTP_HX_REQUEST="true"
    )

    assert 'data-testid="entry-form"' in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == Entry.Status.WANT_TO_WATCH


def test_cancel_and_edit_links_target_the_panel(owner_client, entry):
    panel = owner_client.get(
        reverse("library:entry_detail", args=[entry.pk]), HTTP_HX_REQUEST="true"
    ).content.decode()
    form = owner_client.get(edit_url(entry), HTTP_HX_REQUEST="true").content.decode()

    assert f'hx-get="{edit_url(entry)}"' in panel
    assert f'hx-get="{reverse("library:entry_detail", args=[entry.pk])}"' in form


# --- Library card status control -------------------------------------------------------


def status_url(entry):
    return reverse("library:entry_status", args=[entry.pk])


def test_card_status_change_updates_entry_and_returns_card(owner_client, entry):
    response = owner_client.post(status_url(entry), {"status": "watching"}, HTTP_HX_REQUEST="true")
    html = response.content.decode()

    assert "<html" not in html
    assert f'id="entry-card-{entry.pk}"' in html
    assert re.search(r'value="watching"\s+selected', html)
    entry.refresh_from_db()
    assert entry.status == "watching"


def test_card_status_change_away_from_watched_clears_fields(owner_client, watched_entry):
    owner_client.post(
        status_url(watched_entry), {"status": "want_to_watch"}, HTTP_HX_REQUEST="true"
    )

    watched_entry.refresh_from_db()
    assert watched_entry.status == "want_to_watch"
    assert (watched_entry.rating, watched_entry.date_watched) == (None, None)
    assert watched_entry.times_watched == 0


def test_card_status_with_invalid_value_leaves_entry_and_shows_error(owner_client, entry):
    response = owner_client.post(status_url(entry), {"status": "dropped"}, HTTP_HX_REQUEST="true")

    assert 'role="alert"' in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == Entry.Status.WANT_TO_WATCH


def test_card_status_rejects_get_and_redirects_without_htmx(owner_client, entry):
    assert owner_client.get(status_url(entry)).status_code == 405

    response = owner_client.post(status_url(entry), {"status": "watched"})
    assert response.status_code == 302
    assert response["Location"] == reverse("library:index")


def test_library_card_links_to_entry_page_and_has_status_control(owner_client, entry):
    html = owner_client.get(reverse("library:index")).content.decode()

    assert f'href="{reverse("library:entry_detail", args=[entry.pk])}"' in html
    assert f'hx-post="{status_url(entry)}"' in html
    assert 'hx-trigger="change"' in html
