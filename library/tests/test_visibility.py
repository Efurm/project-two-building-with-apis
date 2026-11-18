import re

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from library.models import Entry, ListItem, MovieList

PRIVATE = MovieList.Visibility.PRIVATE
PUBLIC = MovieList.Visibility.PUBLIC
SHARED = MovieList.Visibility.SHARED


@pytest.mark.django_db
def test_visible_to_applies_owner_public_and_shared_rules(owner, shared_user, stranger):
    mine_private = MovieList.objects.create(owner=owner, name="Mine private", visibility=PRIVATE)
    mine_public = MovieList.objects.create(owner=owner, name="Mine public", visibility=PUBLIC)
    mine_shared = MovieList.objects.create(owner=owner, name="Mine shared", visibility=SHARED)
    mine_shared.shared_with.add(shared_user)
    # A private list that still names shared_user: sharing only applies when visibility is Shared.
    private_named = MovieList.objects.create(owner=owner, name="Private named", visibility=PRIVATE)
    private_named.shared_with.add(shared_user)
    theirs_public = MovieList.objects.create(
        owner=stranger, name="Theirs public", visibility=PUBLIC
    )
    theirs_shared_with_me = MovieList.objects.create(
        owner=stranger, name="Theirs shared with owner", visibility=SHARED
    )
    theirs_shared_with_me.shared_with.add(owner)
    MovieList.objects.create(owner=stranger, name="Theirs private", visibility=PRIVATE)

    def names(user):
        return sorted(MovieList.objects.visible_to(user).values_list("name", flat=True))

    assert names(owner) == sorted(
        [
            mine_private.name,
            mine_public.name,
            mine_shared.name,
            private_named.name,
            theirs_public.name,
            theirs_shared_with_me.name,
        ]
    )
    assert names(shared_user) == sorted([mine_public.name, mine_shared.name, theirs_public.name])
    assert names(stranger) == sorted(
        [mine_public.name, theirs_public.name, theirs_shared_with_me.name, "Theirs private"]
    )
    assert names(AnonymousUser()) == sorted([mine_public.name, theirs_public.name])


@pytest.fixture
def shared_list(owner, shared_user, make_movie):
    movie_list = MovieList.objects.create(owner=owner, name="Date night", visibility=SHARED)
    movie_list.shared_with.add(shared_user)
    entry = Entry.objects.create(user=owner, movie=make_movie())
    ListItem.objects.create(movie_list=movie_list, entry=entry)
    return movie_list


WRITE_ACTIONS = [
    (
        "rename",
        lambda lst, entry, user: (reverse("lists:rename", args=[lst.pk]), {"name": "Hacked"}),
    ),
    ("delete", lambda lst, entry, user: (reverse("lists:delete", args=[lst.pk]), {})),
    (
        "add_item",
        lambda lst, entry, user: (reverse("lists:add_item", args=[lst.pk]), {"entry": entry.pk}),
    ),
    (
        "remove_item",
        lambda lst, entry, user: (reverse("lists:remove_item", args=[lst.pk, entry.pk]), {}),
    ),
    (
        "visibility",
        lambda lst, entry, user: (
            reverse("lists:visibility", args=[lst.pk]),
            {"visibility": "private"},
        ),
    ),
    (
        "share_add",
        lambda lst, entry, user: (
            reverse("lists:share_add", args=[lst.pk]),
            {"username": user.username},
        ),
    ),
    (
        "share_remove",
        lambda lst, entry, user: (reverse("lists:share_remove", args=[lst.pk, user.pk]), {}),
    ),
]


@pytest.mark.parametrize("list_visibility", [SHARED, PUBLIC])
@pytest.mark.parametrize("viewer", ["shared_user", "stranger"])
@pytest.mark.parametrize(("action", "build"), WRITE_ACTIONS, ids=[a for a, _ in WRITE_ACTIONS])
def test_viewers_who_are_not_the_owner_cannot_change_a_list_they_can_see(
    request, client, shared_list, list_visibility, viewer, action, build
):
    shared_list.visibility = list_visibility
    shared_list.save()
    user = request.getfixturevalue(viewer)
    entry = shared_list.items.get().entry
    client.force_login(user)
    before = (
        shared_list.name,
        shared_list.visibility,
        set(shared_list.shared_with.values_list("pk", flat=True)),
        set(shared_list.items.values_list("entry", flat=True)),
    )

    url, data = build(shared_list, entry, user)
    response = client.post(url, data, HTTP_HX_REQUEST="true")

    assert response.status_code == 404
    shared_list.refresh_from_db()
    after = (
        shared_list.name,
        shared_list.visibility,
        set(shared_list.shared_with.values_list("pk", flat=True)),
        set(shared_list.items.values_list("entry", flat=True)),
    )
    assert after == before


def field_block(html, name):
    """The HTML of the form-field wrapper marked data-field="<name>" (None if absent)."""
    match = re.search(rf'<fieldset[^>]*data-field="{name}".*?</fieldset>', html, re.S)
    return match.group(0) if match else None


def test_sharing_with_unknown_username_shows_error_and_shares_with_nobody(owner_client, owner):
    movie_list = MovieList.objects.create(owner=owner, name="Date night", visibility=SHARED)

    response = owner_client.post(
        reverse("lists:share_add", args=[movie_list.pk]),
        {"username": "nosuchuser"},
        HTTP_HX_REQUEST="true",
    )
    html = response.content.decode()

    assert response.status_code == 200
    username_block = field_block(html, "username")
    assert username_block is not None
    assert "No account has the username nosuchuser." in username_block
    assert 'value="nosuchuser"' in username_block
    assert not movie_list.shared_with.exists()


# --- Ordinary tests ---------------------------------------------------------------------

# Expected website read access: viewer -> visibilities they may read.
CAN_READ = {
    "owner": {PRIVATE, PUBLIC, SHARED},
    "shared_user": {PUBLIC, SHARED},
    "stranger": {PUBLIC},
    "anonymous": {PUBLIC},
}


@pytest.mark.parametrize("list_visibility", [PRIVATE, PUBLIC, SHARED])
@pytest.mark.parametrize("viewer", list(CAN_READ))
@pytest.mark.parametrize("htmx", [False, True], ids=["page", "htmx-browse"])
def test_website_list_read_matrix(request, client, shared_list, list_visibility, viewer, htmx):
    shared_list.visibility = list_visibility
    shared_list.save()
    if viewer != "anonymous":
        client.force_login(request.getfixturevalue(viewer))
    headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}

    response = client.get(reverse("lists:detail", args=[shared_list.pk]), **headers)

    expected = 200 if list_visibility in CAN_READ[viewer] else 404
    assert response.status_code == expected


def test_viewer_sees_owner_data_read_only_without_owner_controls(client, shared_user, shared_list):
    entry = shared_list.items.get().entry
    entry.status = Entry.Status.WATCHED
    entry.rating = 4
    entry.notes = "Owner's thoughts."
    entry.save()
    client.force_login(shared_user)

    html = client.get(reverse("lists:detail", args=[shared_list.pk])).content.decode()

    assert "Owner&#x27;s thoughts." in html
    assert 'aria-label="4 out of 5 stars"' in html
    assert "Watched" in html
    assert "A shared list by" in html and reverse("profile", args=["owner"]) in html
    assert 'data-testid="list-sharing"' not in html
    assert "Rename" not in html and "Delete list" not in html
    assert "Remove from list" not in html
    assert reverse("library:entry_detail", args=[entry.pk]) not in html


def test_owner_sees_sharing_panel_and_controls(owner_client, shared_list):
    html = owner_client.get(reverse("lists:detail", args=[shared_list.pk])).content.decode()

    assert 'data-testid="list-sharing"' in html
    assert "friend" in html
    assert "Rename" in html and "Remove from list" in html


def test_entries_stay_owner_only_even_when_in_a_public_list(client, stranger, shared_list):
    shared_list.visibility = PUBLIC
    shared_list.save()
    entry = shared_list.items.get().entry
    client.force_login(stranger)

    assert client.get(reverse("library:entry_detail", args=[entry.pk])).status_code == 404
    assert entry.movie.title not in client.get(reverse("library:index")).content.decode()


def test_profile_shows_only_public_lists_and_works_signed_out(anon_client, owner, shared_list):
    MovieList.objects.create(owner=owner, name="Public picks", visibility=PUBLIC)
    MovieList.objects.create(owner=owner, name="Secret", visibility=PRIVATE)

    response = anon_client.get(reverse("profile", args=["owner"]))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Public picks" in html
    assert "Secret" not in html and "Date night" not in html


def test_profile_of_unknown_user_is_404(anon_client, db):
    assert anon_client.get(reverse("profile", args=["nobody"])).status_code == 404


def test_shared_with_me_lists_only_currently_shared_lists(
    client, shared_user, owner, stranger, shared_list
):
    switched_off = MovieList.objects.create(owner=stranger, name="Was shared", visibility=PRIVATE)
    switched_off.shared_with.add(shared_user)
    MovieList.objects.create(owner=stranger, name="Just public", visibility=PUBLIC)
    client.force_login(shared_user)

    html = client.get(reverse("shared")).content.decode()

    assert "Date night" in html and "by owner" in html
    assert "Was shared" not in html and "Just public" not in html


def test_shared_with_me_requires_sign_in(anon_client):
    response = anon_client.get(reverse("shared"))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


@pytest.mark.parametrize(
    ("value", "help_text"),
    [
        (PUBLIC, "Anyone can see this list"),
        (PRIVATE, "Only you can see this list."),
        (SHARED, "Only you and the people below"),
    ],
)
def test_owner_sets_visibility_and_panel_explains_it(owner_client, shared_list, value, help_text):
    html = owner_client.post(
        reverse("lists:visibility", args=[shared_list.pk]),
        {"visibility": value},
        HTTP_HX_REQUEST="true",
    ).content.decode()

    shared_list.refresh_from_db()
    assert shared_list.visibility == value
    assert help_text in html


def test_invalid_visibility_value_is_ignored(owner_client, shared_list):
    owner_client.post(
        reverse("lists:visibility", args=[shared_list.pk]),
        {"visibility": "everyone"},
        HTTP_HX_REQUEST="true",
    )

    shared_list.refresh_from_db()
    assert shared_list.visibility == SHARED


def test_owner_shares_and_unshares_by_username(owner_client, shared_list, stranger, shared_user):
    add = owner_client.post(
        reverse("lists:share_add", args=[shared_list.pk]),
        {"username": " stranger "},
        HTTP_HX_REQUEST="true",
    ).content.decode()
    assert set(shared_list.shared_with.values_list("username", flat=True)) == {
        "friend",
        "stranger",
    }
    assert "Stop sharing with stranger" in add

    owner_client.post(
        reverse("lists:share_remove", args=[shared_list.pk, shared_user.pk]),
        HTTP_HX_REQUEST="true",
    )
    assert list(shared_list.shared_with.values_list("username", flat=True)) == ["stranger"]


def test_sharing_twice_keeps_one_and_sharing_with_self_is_rejected(
    owner_client, shared_list, shared_user
):
    url = reverse("lists:share_add", args=[shared_list.pk])

    owner_client.post(url, {"username": "friend"}, HTTP_HX_REQUEST="true")
    html = owner_client.post(url, {"username": "owner"}, HTTP_HX_REQUEST="true").content.decode()

    assert shared_list.shared_with.count() == 1
    assert "You own this list, so you can always see it." in field_block(html, "username")


def test_non_htmx_share_error_redirects_back_with_message(owner_client, shared_list):
    response = owner_client.post(
        reverse("lists:share_add", args=[shared_list.pk]), {"username": "ghost"}, follow=True
    )

    assert response.redirect_chain[-1][0] == reverse("lists:detail", args=[shared_list.pk])
    assert "No account has the username ghost." in response.content.decode()


def test_lists_index_shows_visibility_badges(owner_client, shared_list):
    html = owner_client.get(reverse("lists:index")).content.decode()

    assert re.search(r'data-testid="visibility-badge">Shared · 1<', html)


def test_navbar_links_to_shared_with_me_and_profile(owner_client):
    html = owner_client.get(reverse("library:index")).content.decode()

    assert f'href="{reverse("shared")}"' in html
    assert f'href="{reverse("profile", args=["owner"])}"' in html
