import datetime

from django.urls import reverse

from library.models import Entry


def test_library_lists_only_own_entries_newest_first(owner_client, owner, stranger, make_movie):
    first = Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, title="Alpha Film"))
    second = Entry.objects.create(
        user=owner,
        movie=make_movie(tmdb_id=2, title="Beta Film", release_date=datetime.date(1999, 3, 31)),
        status=Entry.Status.WATCHED,
    )
    Entry.objects.create(user=stranger, movie=make_movie(tmdb_id=3, title="Strangers Film"))

    response = owner_client.get(reverse("library:index"))
    content = response.content.decode()

    assert list(response.context["entries"]) == [second, first]
    assert "Alpha Film" in content and "Beta Film" in content
    assert "(1999)" in content
    assert "Watched" in content and "Want to watch" in content
    assert "Strangers Film" not in content
    assert "Your library is empty" not in content


def test_library_renders_from_local_data_without_tmdb(owner_client, owner, make_movie):
    # The autouse fixture makes any real HTTP request fail the test.
    Entry.objects.create(user=owner, movie=make_movie(poster_path="/abc.jpg"))

    response = owner_client.get(reverse("library:index"))

    assert response.status_code == 200
    assert b"Inception" in response.content


def test_library_poster_uses_tmdb_url_with_placeholder_fallback(owner_client, owner, make_movie):
    Entry.objects.create(user=owner, movie=make_movie(tmdb_id=1, poster_path="/abc.jpg"))
    Entry.objects.create(user=owner, movie=make_movie(tmdb_id=2, title="No Poster"))

    content = owner_client.get(reverse("library:index")).content.decode()

    assert 'src="https://image.tmdb.org/t/p/w185/abc.jpg"' in content
    assert 'src="/static/img/poster-placeholder.svg"' in content
    assert content.count('onerror="') == 2
