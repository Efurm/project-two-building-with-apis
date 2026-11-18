import pytest
from django.urls import reverse

from library.models import Entry, ListItem, MovieList


@pytest.fixture
def my_list(owner):
    return MovieList.objects.create(owner=owner, name="Date night")


def test_adding_another_users_entry_to_my_list_is_refused(
    owner_client, my_list, stranger, make_movie
):
    strangers_entry = Entry.objects.create(user=stranger, movie=make_movie())

    response = owner_client.post(
        reverse("lists:add_item", args=[my_list.pk]),
        {"entry": strangers_entry.pk},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 404
    assert not ListItem.objects.exists()


def test_deleting_a_list_removes_its_items_but_keeps_the_entries(
    owner_client, owner, my_list, make_movie
):
    first = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="One"))
    second = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=2, title="Two"))
    other_list = MovieList.objects.create(owner=owner, name="Best horror")
    ListItem.objects.create(movie_list=my_list, entry=first)
    ListItem.objects.create(movie_list=my_list, entry=second)
    ListItem.objects.create(movie_list=other_list, entry=first)

    response = owner_client.post(reverse("lists:delete", args=[my_list.pk]))

    assert response.status_code == 302
    assert not MovieList.objects.filter(pk=my_list.pk).exists()
    assert not ListItem.objects.filter(movie_list_id=my_list.pk).exists()
    assert set(Entry.objects.filter(user=owner)) == {first, second}
    assert list(other_list.items.values_list("entry", flat=True)) == [first.pk]


def test_entry_delete_confirmation_counts_lists_and_confirming_deletes_entry_and_items(
    owner_client, owner, my_list, make_movie
):
    entry = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Heat"))
    keeper = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=2, title="Ronin"))
    horror = MovieList.objects.create(owner=owner, name="Best horror")
    MovieList.objects.create(owner=owner, name="Unrelated")
    ListItem.objects.create(movie_list=my_list, entry=entry)
    ListItem.objects.create(movie_list=horror, entry=entry)
    ListItem.objects.create(movie_list=my_list, entry=keeper)
    delete_url = reverse("library:entry_delete", args=[entry.pk])

    confirm = owner_client.get(delete_url, HTTP_HX_REQUEST="true").content.decode()

    assert "It will also be removed from 2 of your lists." in confirm
    assert Entry.objects.filter(pk=entry.pk).exists()

    owner_client.post(delete_url, HTTP_HX_REQUEST="true")

    assert not Entry.objects.filter(pk=entry.pk).exists()
    assert not ListItem.objects.filter(entry_id=entry.pk).exists()
    assert list(my_list.items.values_list("entry", flat=True)) == [keeper.pk]
    assert MovieList.objects.filter(owner=owner).count() == 3


# --- Ordinary tests ---------------------------------------------------------------------


@pytest.fixture
def entry(owner, make_movie):
    return Entry.objects.create(
        user=owner,
        movie=make_movie(tmdb_id=10, title="Heat"),
        status=Entry.Status.WATCHED,
        rating=5,
        notes="Best diner scene ever.",
    )


def test_lists_index_shows_only_my_lists_with_counts(owner_client, owner, stranger, my_list, entry):
    ListItem.objects.create(movie_list=my_list, entry=entry)
    MovieList.objects.create(owner=owner, name="Empty one")
    MovieList.objects.create(owner=stranger, name="Strangers list")

    html = owner_client.get(reverse("lists:index")).content.decode()

    assert "Date night" in html and "1 movie<" in html
    assert "Empty one" in html and "0 movies" in html
    assert "Strangers list" not in html


def test_create_list_redirects_to_it(owner_client, owner):
    response = owner_client.post(reverse("lists:index"), {"name": "  Best horror  "})

    movie_list = MovieList.objects.get(owner=owner)
    assert movie_list.name == "Best horror"
    assert response["Location"] == reverse("lists:detail", args=[movie_list.pk])


def test_create_list_with_blank_name_shows_error(owner_client):
    response = owner_client.post(reverse("lists:index"), {"name": "   "})

    assert response.status_code == 200
    assert not MovieList.objects.exists()
    assert "Give the list a name." in response.content.decode()


def test_rename_list_via_htmx_returns_header(owner_client, my_list):
    html = owner_client.post(
        reverse("lists:rename", args=[my_list.pk]), {"name": "Movie night"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    my_list.refresh_from_db()
    assert my_list.name == "Movie night"
    assert 'id="list-header"' in html and "Movie night" in html


def test_rename_with_blank_name_returns_form_with_error(owner_client, my_list):
    html = owner_client.post(
        reverse("lists:rename", args=[my_list.pk]), {"name": ""}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert 'data-testid="rename-form"' in html
    my_list.refresh_from_db()
    assert my_list.name == "Date night"


def test_list_delete_confirmation_says_movies_stay(owner_client, my_list, entry):
    ListItem.objects.create(movie_list=my_list, entry=entry)

    html = owner_client.get(
        reverse("lists:delete", args=[my_list.pk]), HTTP_HX_REQUEST="true"
    ).content.decode()

    assert "Its 1 movie will stay in your library." in html
    assert MovieList.objects.filter(pk=my_list.pk).exists()


def test_htmx_list_delete_redirects_client_to_lists(owner_client, my_list):
    response = owner_client.post(reverse("lists:delete", args=[my_list.pk]), HTTP_HX_REQUEST="true")

    assert response["HX-Redirect"] == reverse("lists:index")


def test_add_entry_returns_entry_lists_panel_and_ignores_duplicates(owner_client, my_list, entry):
    url = reverse("lists:add_item", args=[my_list.pk])

    owner_client.post(url, {"entry": entry.pk}, HTTP_HX_REQUEST="true")
    html = owner_client.post(url, {"entry": entry.pk}, HTTP_HX_REQUEST="true").content.decode()

    assert ListItem.objects.filter(movie_list=my_list, entry=entry).count() == 1
    assert 'id="entry-lists"' in html
    assert "Date night" in html


def test_same_entry_can_be_in_several_lists(owner_client, owner, my_list, entry):
    other = MovieList.objects.create(owner=owner, name="Crime")

    for movie_list in (my_list, other):
        owner_client.post(
            reverse("lists:add_item", args=[movie_list.pk]),
            {"entry": entry.pk},
            HTTP_HX_REQUEST="true",
        )

    names = set(entry.list_items.values_list("movie_list__name", flat=True))
    assert names == {"Date night", "Crime"}


def test_remove_from_entry_page_returns_panel_and_keeps_entry(owner_client, my_list, entry):
    ListItem.objects.create(movie_list=my_list, entry=entry)

    html = owner_client.post(
        reverse("lists:remove_item", args=[my_list.pk, entry.pk]),
        {"panel": "1"},
        HTTP_HX_REQUEST="true",
    ).content.decode()

    assert not ListItem.objects.exists()
    assert Entry.objects.filter(pk=entry.pk).exists()
    assert "Not in any of your lists." in html


def test_remove_from_list_page_returns_empty_for_card_removal(owner_client, my_list, entry):
    ListItem.objects.create(movie_list=my_list, entry=entry)

    response = owner_client.post(
        reverse("lists:remove_item", args=[my_list.pk, entry.pk]), HTTP_HX_REQUEST="true"
    )

    assert response.status_code == 200
    assert response.content == b""
    assert not ListItem.objects.exists()


def test_list_detail_shows_only_its_entries_with_status_rating_and_notes(
    owner_client, owner, my_list, entry, make_movie
):
    ListItem.objects.create(movie_list=my_list, entry=entry)
    Entry.objects.create(user=owner, movie=make_movie(tmdb_id=11, title="Not In List"))

    html = owner_client.get(reverse("lists:detail", args=[my_list.pk])).content.decode()

    assert "Heat" in html and "Not In List" not in html
    assert "Watched" in html
    assert 'aria-label="5 out of 5 stars"' in html
    assert "Best diner scene ever." in html
    assert "Remove from list" in html


def test_list_detail_supports_browse_parameters_and_htmx_partial(
    owner_client, owner, my_list, make_movie
):
    for n, title in enumerate(["Alpha", "Bravo", "Charlie"]):
        e = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=20 + n, title=title))
        ListItem.objects.create(movie_list=my_list, entry=e)
    url = reverse("lists:detail", args=[my_list.pk])

    response = owner_client.get(
        url, {"q": "a", "sort": "title", "dir": "desc"}, HTTP_HX_REQUEST="true"
    )
    html = response.content.decode()

    assert [e.movie.title for e in response.context["entries"]] == ["Charlie", "Bravo", "Alpha"]
    assert "<html" not in html
    assert f'hx-get="{url}"' in html


def test_empty_list_shows_list_specific_empty_message(owner_client, my_list):
    html = owner_client.get(reverse("lists:detail", args=[my_list.pk])).content.decode()

    assert "This list is empty." in html


def test_entry_page_shows_lists_panel_and_add_options(owner_client, owner, my_list, entry):
    other = MovieList.objects.create(owner=owner, name="Crime")
    ListItem.objects.create(movie_list=my_list, entry=entry)

    html = owner_client.get(reverse("library:entry_detail", args=[entry.pk])).content.decode()

    assert 'id="entry-lists"' in html
    assert reverse("lists:remove_item", args=[my_list.pk, entry.pk]) in html
    assert f'hx-post="{reverse("lists:add_item", args=[other.pk])}"' in html
    assert f'hx-post="{reverse("lists:add_item", args=[my_list.pk])}"' not in html


def test_entry_delete_without_lists_omits_list_sentence_and_htmx_redirects(owner_client, entry):
    url = reverse("library:entry_delete", args=[entry.pk])

    confirm = owner_client.get(url, HTTP_HX_REQUEST="true").content.decode()
    response = owner_client.post(url, HTTP_HX_REQUEST="true")

    assert "Delete Heat from your library?" in confirm
    assert "removed from" not in confirm
    assert response["HX-Redirect"] == reverse("library:index")
    assert not Entry.objects.exists()


def test_non_htmx_entry_delete_redirects_with_message(owner_client, entry):
    response = owner_client.post(reverse("library:entry_delete", args=[entry.pk]), follow=True)

    assert response.redirect_chain[-1][0] == reverse("library:index")
    assert "Deleted “Heat” from your library." in response.content.decode()


@pytest.mark.parametrize(
    ("method", "url_name", "needs_entry"),
    [
        ("get", "lists:detail", False),
        ("get", "lists:rename", False),
        ("post", "lists:rename", False),
        ("get", "lists:delete", False),
        ("post", "lists:delete", False),
        ("post", "lists:add_item", False),
        ("post", "lists:remove_item", True),
    ],
)
def test_other_users_lists_return_404(
    client, stranger, my_list, entry, method, url_name, needs_entry
):
    ListItem.objects.create(movie_list=my_list, entry=entry)
    args = [my_list.pk, entry.pk] if needs_entry else [my_list.pk]
    client.force_login(stranger)

    response = getattr(client, method)(
        reverse(url_name, args=args), {"name": "x", "entry": entry.pk}
    )

    assert response.status_code == 404
    my_list.refresh_from_db()
    assert my_list.name == "Date night"
    assert ListItem.objects.count() == 1


def test_stranger_cannot_delete_my_entry(client, stranger, entry):
    client.force_login(stranger)

    assert client.post(reverse("library:entry_delete", args=[entry.pk])).status_code == 404
    assert Entry.objects.filter(pk=entry.pk).exists()


def test_lists_pages_require_sign_in(anon_client, my_list):
    for url in (reverse("lists:index"), reverse("lists:detail", args=[my_list.pk])):
        response = anon_client.get(url)
        assert response.status_code == 302
        assert response["Location"].startswith(reverse("accounts:login"))


def test_navbar_links_to_lists(owner_client):
    html = owner_client.get(reverse("library:index")).content.decode()

    assert f'href="{reverse("lists:index")}"' in html
