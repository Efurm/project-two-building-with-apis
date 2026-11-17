from urllib.parse import parse_qs, urlsplit

from django.urls import reverse


def test_signed_out_library_request_redirects_to_login_with_next(anon_client):
    library_url = reverse("library:index")

    response = anon_client.get(library_url)

    assert response.status_code == 302
    location = urlsplit(response["Location"])
    assert location.path == reverse("accounts:login")
    assert parse_qs(location.query) == {"next": [library_url]}
