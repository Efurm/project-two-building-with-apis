from django.urls import reverse
from rest_framework.authtoken.models import Token


def test_my_account_requires_sign_in(anon_client):
    response = anon_client.get(reverse("accounts:me"))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


def test_my_account_without_token_offers_to_generate(owner_client):
    html = owner_client.get(reverse("accounts:me")).content.decode()

    assert "have an API token yet." in html
    assert "Generate token" in html


def test_generate_then_regenerate_replaces_the_token(owner_client, owner, api_client):
    first = owner_client.post(reverse("accounts:me"), follow=True)
    old_key = Token.objects.get(user=owner).key
    assert old_key in first.content.decode()
    assert "Generated your API token." in first.content.decode()

    second = owner_client.post(reverse("accounts:me"), follow=True)
    new_key = Token.objects.get(user=owner).key
    assert new_key != old_key
    assert "The old one no longer works." in second.content.decode()

    api_client.credentials(HTTP_AUTHORIZATION=f"Token {old_key}")
    assert api_client.get("/api/entries/").status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {new_key}")
    assert api_client.get("/api/entries/").status_code == 200


def test_navbar_links_to_my_account(owner_client):
    html = owner_client.get(reverse("library:index")).content.decode()

    assert f'href="{reverse("accounts:me")}"' in html
