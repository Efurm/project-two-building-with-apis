import pytest
from django.urls import reverse


def test_home_redirects_to_library(anon_client):
    response = anon_client.get(reverse("home"))

    assert response.status_code == 302
    assert response["Location"] == reverse("library:index")


def test_signed_in_user_sees_empty_library(owner_client, owner):
    response = owner_client.get(reverse("library:index"))

    assert response.status_code == 200
    assert b"Your library is empty" in response.content
    assert owner.username.encode() in response.content


@pytest.mark.parametrize("url_name", ["accounts:login", "accounts:signup"])
def test_public_pages_show_tmdb_attribution(anon_client, url_name, db):
    response = anon_client.get(reverse(url_name))

    assert response.status_code == 200
    assert b'data-testid="tmdb-attribution"' in response.content
    assert b"not endorsed or certified by TMDB" in response.content


def test_library_page_shows_tmdb_attribution(owner_client):
    response = owner_client.get(reverse("library:index"))

    assert b"not endorsed or certified by TMDB" in response.content


def test_pages_load_local_css_and_htmx_not_cdn(owner_client):
    content = owner_client.get(reverse("library:index")).content.decode()

    assert "/static/css/app.css" in content
    assert "/static/js/htmx.min.js" in content
    assert "cdn." not in content and "unpkg.com" not in content
