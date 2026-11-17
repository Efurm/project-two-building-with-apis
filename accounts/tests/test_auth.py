import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from conftest import PASSWORD


@pytest.mark.django_db
def test_signup_with_mismatched_passwords_shows_field_error(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "newviewer", "password1": "a-long-passphrase-1", "password2": "different-2"},
    )

    assert response.status_code == 200
    assert not get_user_model().objects.filter(username="newviewer").exists()
    assert "password2" in response.context["form"].errors
    assert not response.context["user"].is_authenticated


@pytest.mark.django_db
def test_signup_with_taken_username_is_rejected(client, owner):
    response = client.post(
        reverse("accounts:signup"),
        {"username": owner.username, "password1": "a-long-pass-99", "password2": "a-long-pass-99"},
    )

    assert response.status_code == 200
    assert "username" in response.context["form"].errors


def test_login_with_valid_credentials_lands_on_library(client, owner):
    response = client.post(
        reverse("accounts:login"),
        {"username": owner.username, "password": PASSWORD},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("library:index")
    assert response.context["user"] == owner


def test_login_honors_next_parameter(client, owner):
    response = client.post(
        reverse("accounts:login"),
        {"username": owner.username, "password": PASSWORD, "next": reverse("library:index")},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("library:index")


def test_login_with_wrong_password_shows_error(client, owner):
    response = client.post(
        reverse("accounts:login"),
        {"username": owner.username, "password": "wrong"},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert not response.context["user"].is_authenticated


def test_logout_signs_user_out(owner_client):
    response = owner_client.post(reverse("accounts:logout"), follow=True)

    assert not response.context["user"].is_authenticated
    assert owner_client.get(reverse("library:index")).status_code == 302
