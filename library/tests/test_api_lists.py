import pytest

from library.models import Entry, ListItem, MovieList

PRIVATE = MovieList.Visibility.PRIVATE
PUBLIC = MovieList.Visibility.PUBLIC
SHARED = MovieList.Visibility.SHARED

# Expected API read access: viewer -> visibilities they may read (same as the website).
CAN_READ = {
    "owner": {PRIVATE, PUBLIC, SHARED},
    "shared_user": {PUBLIC, SHARED},
    "stranger": {PUBLIC},
    "anonymous": {PUBLIC},
}


@pytest.fixture
def shared_list(owner, shared_user, make_movie):
    movie_list = MovieList.objects.create(owner=owner, name="Date night", visibility=SHARED)
    movie_list.shared_with.add(shared_user)
    entry = Entry.objects.create(user=owner, movie=make_movie(), notes="Owner note.")
    ListItem.objects.create(movie_list=movie_list, entry=entry)
    return movie_list


def client_for(request, api_client, viewer):
    if viewer != "anonymous":
        api_client.force_authenticate(request.getfixturevalue(viewer))
    return api_client


@pytest.mark.parametrize("list_visibility", [PRIVATE, PUBLIC, SHARED])
@pytest.mark.parametrize("viewer", list(CAN_READ))
def test_api_list_read_matrix_matches_the_website(
    request, api_client, shared_list, list_visibility, viewer
):
    shared_list.visibility = list_visibility
    shared_list.save()
    client = client_for(request, api_client, viewer)

    detail = client.get(f"/api/lists/{shared_list.pk}/")
    items = client.get(f"/api/lists/{shared_list.pk}/items/")

    expected = 200 if list_visibility in CAN_READ[viewer] else 404
    assert (detail.status_code, items.status_code) == (expected, expected)
    if expected == 200:
        assert detail.json()["name"] == "Date night"
        assert [i["notes"] for i in items.json()["results"]] == ["Owner note."]


def snapshot(movie_list):
    movie_list.refresh_from_db()
    return (
        movie_list.name,
        movie_list.visibility,
        set(movie_list.shared_with.values_list("username", flat=True)),
        set(movie_list.items.values_list("entry", flat=True)),
    )


WRITES = {
    "patch": lambda c, lst, e: c.patch(f"/api/lists/{lst.pk}/", {"name": "Hacked"}, format="json"),
    "put": lambda c, lst, e: c.put(
        f"/api/lists/{lst.pk}/", {"name": "Hacked", "visibility": "public"}, format="json"
    ),
    "delete": lambda c, lst, e: c.delete(f"/api/lists/{lst.pk}/"),
    "add_item": lambda c, lst, e: c.post(
        f"/api/lists/{lst.pk}/items/", {"entry": e.pk}, format="json"
    ),
    "remove_item": lambda c, lst, e: c.delete(f"/api/lists/{lst.pk}/items/{e.pk}/"),
}


@pytest.mark.parametrize("list_visibility", [SHARED, PUBLIC])
@pytest.mark.parametrize(
    ("viewer", "expected_status"),
    [("shared_user", 404), ("stranger", 404), ("anonymous", 401)],
)
@pytest.mark.parametrize("write", list(WRITES))
def test_non_owners_cannot_change_a_list_through_the_api(
    request, api_client, shared_list, make_movie, list_visibility, viewer, expected_status, write
):
    shared_list.visibility = list_visibility
    shared_list.save()
    owner_entry = shared_list.items.get().entry
    if viewer != "anonymous":
        # The viewer's own entry, so "add item" can't fail just because the entry is foreign.
        own_entry = Entry.objects.create(
            user=request.getfixturevalue(viewer), movie=make_movie(tmdb_id=99, title="Mine")
        )
    entry = owner_entry if write == "remove_item" or viewer == "anonymous" else own_entry
    before = snapshot(shared_list)
    client = client_for(request, api_client, viewer)

    response = WRITES[write](client, shared_list, entry)

    assert response.status_code == expected_status
    assert snapshot(shared_list) == before


def test_shared_with_is_written_as_usernames_and_unknown_ones_are_rejected(
    api_client, owner, shared_user, stranger
):
    movie_list = MovieList.objects.create(owner=owner, name="Date night")
    api_client.force_authenticate(owner)
    url = f"/api/lists/{movie_list.pk}/"

    shared = api_client.patch(
        url, {"visibility": "shared", "shared_with": ["friend", "stranger"]}, format="json"
    )

    assert shared.status_code == 200
    assert shared.json()["shared_with"] == ["friend", "stranger"]
    assert snapshot(movie_list) == ("Date night", SHARED, {"friend", "stranger"}, set())

    rejected = api_client.patch(
        url, {"name": "Renamed", "shared_with": ["friend", "ghost"]}, format="json"
    )

    assert rejected.status_code == 400
    assert rejected.json() == {"shared_with": ["No account has the username ghost."]}
    assert snapshot(movie_list) == ("Date night", SHARED, {"friend", "stranger"}, set())


# --- Ordinary tests ---------------------------------------------------------------------


@pytest.fixture
def owner_api(api_client, owner):
    api_client.force_authenticate(owner)
    return api_client


def names(response):
    return sorted(item["name"] for item in response.json()["results"])


@pytest.fixture
def many_lists(owner, shared_user, stranger):
    MovieList.objects.create(owner=owner, name="Owner private")
    MovieList.objects.create(owner=owner, name="Owner public", visibility=PUBLIC)
    shared = MovieList.objects.create(owner=owner, name="Owner shared", visibility=SHARED)
    shared.shared_with.add(shared_user)
    MovieList.objects.create(owner=stranger, name="Stranger public", visibility=PUBLIC)
    MovieList.objects.create(owner=stranger, name="Stranger private")


def test_listing_returns_lists_visible_to_the_requester(
    request, api_client, shared_user, many_lists
):
    assert names(api_client.get("/api/lists/")) == ["Owner public", "Stranger public"]

    api_client.force_authenticate(shared_user)
    assert names(api_client.get("/api/lists/")) == [
        "Owner public",
        "Owner shared",
        "Stranger public",
    ]


def test_shared_with_me_filter_mirrors_the_shared_page(api_client, shared_user, many_lists):
    api_client.force_authenticate(shared_user)

    assert names(api_client.get("/api/lists/", {"shared_with_me": "true"})) == ["Owner shared"]


def test_shared_with_me_filter_is_empty_for_anonymous(api_client, many_lists):
    assert names(api_client.get("/api/lists/", {"shared_with_me": "true"})) == []


def test_owner_filter_mirrors_the_profile_page(api_client, many_lists):
    response = api_client.get("/api/lists/", {"owner": "owner"})

    assert names(response) == ["Owner public"]


def test_owner_filter_for_myself_shows_all_my_lists(owner_api, many_lists):
    assert names(owner_api.get("/api/lists/", {"owner": "owner"})) == [
        "Owner private",
        "Owner public",
        "Owner shared",
    ]


def test_list_detail_shape(owner_api, shared_list):
    body = owner_api.get(f"/api/lists/{shared_list.pk}/").json()

    assert body["owner"] == "owner"
    assert body["visibility"] == "shared"
    assert body["shared_with"] == ["friend"]
    assert body["item_count"] == 1


def test_create_list_sets_owner_and_accepts_visibility_and_sharing(owner_api, owner, shared_user):
    response = owner_api.post(
        "/api/lists/",
        {"name": "Best horror", "visibility": "shared", "shared_with": ["friend"]},
        format="json",
    )

    assert response.status_code == 201
    movie_list = MovieList.objects.get(name="Best horror")
    assert movie_list.owner == owner
    assert response.json()["owner"] == "owner"
    assert snapshot(movie_list) == ("Best horror", SHARED, {"friend"}, set())


def test_create_list_defaults_to_private(owner_api, owner):
    response = owner_api.post("/api/lists/", {"name": "Quiet"}, format="json")

    assert response.json()["visibility"] == "private"
    assert response.json()["shared_with"] == []


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "x", "visibility": "everyone"}, "visibility"),
        ({"name": "x", "shared_with": "friend"}, "shared_with"),
        ({"name": "x", "shared_with": ["owner"]}, "shared_with"),
    ],
)
def test_create_list_rejects_invalid_input(owner_api, payload, field):
    response = owner_api.post("/api/lists/", payload, format="json")

    assert response.status_code == 400
    assert field in response.json()
    assert not MovieList.objects.exists()


def test_sharing_with_self_gives_the_website_message(owner_api, shared_list):
    response = owner_api.patch(
        f"/api/lists/{shared_list.pk}/", {"shared_with": ["owner"]}, format="json"
    )

    assert response.json() == {"shared_with": ["You own this list, so you can always see it."]}


def test_anonymous_cannot_create_a_list(api_client, db):
    assert api_client.post("/api/lists/", {"name": "x"}, format="json").status_code == 401
    assert not MovieList.objects.exists()


def test_owner_renames_and_clears_sharing_with_patch(owner_api, shared_list):
    response = owner_api.patch(
        f"/api/lists/{shared_list.pk}/",
        {"name": "Movie night", "visibility": "public", "shared_with": []},
        format="json",
    )

    assert response.status_code == 200
    assert snapshot(shared_list)[:3] == ("Movie night", PUBLIC, set())


def test_patch_without_shared_with_keeps_recipients(owner_api, shared_list):
    owner_api.patch(f"/api/lists/{shared_list.pk}/", {"name": "Renamed"}, format="json")

    assert snapshot(shared_list)[2] == {"friend"}


def test_owner_deletes_list_and_entries_stay(owner_api, owner, shared_list):
    response = owner_api.delete(f"/api/lists/{shared_list.pk}/")

    assert response.status_code == 204
    assert not MovieList.objects.exists()
    assert not ListItem.objects.exists()
    assert Entry.objects.filter(user=owner).count() == 1


def test_owner_adds_own_entry_201_then_200_for_duplicate(owner_api, owner, shared_list, make_movie):
    entry = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=50, title="Ronin"))
    url = f"/api/lists/{shared_list.pk}/items/"

    first = owner_api.post(url, {"entry": entry.pk}, format="json")
    second = owner_api.post(url, {"entry": entry.pk}, format="json")

    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["movie"]["title"] == "Ronin"
    assert ListItem.objects.filter(movie_list=shared_list, entry=entry).count() == 1


def test_owner_cannot_add_someone_elses_entry(owner_api, shared_list, stranger, make_movie):
    theirs = Entry.objects.create(user=stranger, movie=make_movie(tmdb_id=51, title="Theirs"))

    response = owner_api.post(
        f"/api/lists/{shared_list.pk}/items/", {"entry": theirs.pk}, format="json"
    )

    assert response.status_code == 404
    assert shared_list.items.count() == 1


@pytest.mark.parametrize("payload", [{}, {"entry": "abc"}, {"entry": None}])
def test_add_item_requires_a_valid_entry_id(owner_api, shared_list, payload):
    response = owner_api.post(f"/api/lists/{shared_list.pk}/items/", payload, format="json")

    assert response.status_code == 400
    assert response.json() == {"entry": ["A valid entry id is required."]}


def test_owner_removes_item_and_entry_stays(owner_api, owner, shared_list):
    entry = shared_list.items.get().entry

    response = owner_api.delete(f"/api/lists/{shared_list.pk}/items/{entry.pk}/")

    assert response.status_code == 204
    assert not shared_list.items.exists()
    assert Entry.objects.filter(pk=entry.pk).exists()


def test_removing_an_entry_not_in_the_list_is_404(owner_api, owner, shared_list, make_movie):
    other = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=52, title="Elsewhere"))

    response = owner_api.delete(f"/api/lists/{shared_list.pk}/items/{other.pk}/")

    assert response.status_code == 404


def test_items_accept_browse_parameters(api_client, owner, shared_list, make_movie):
    shared_list.visibility = PUBLIC
    shared_list.save()
    for n, title in enumerate(["Alpha", "Bravo"]):
        entry = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=60 + n, title=title))
        ListItem.objects.create(movie_list=shared_list, entry=entry)

    response = api_client.get(
        f"/api/lists/{shared_list.pk}/items/", {"sort": "title", "dir": "desc", "q": "a"}
    )

    assert [i["movie"]["title"] for i in response.json()["results"]] == ["Bravo", "Alpha"]


def test_anonymous_reads_public_list_items_with_token_free_request(api_client, shared_list):
    shared_list.visibility = PUBLIC
    shared_list.save()

    response = api_client.get(f"/api/lists/{shared_list.pk}/items/")

    assert response.status_code == 200
    assert response.json()["count"] == 1
