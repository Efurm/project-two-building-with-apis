"""Shared pytest fixtures for the whole project."""

import pytest
import requests
from django.contrib.auth import get_user_model
from django.utils import timezone

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    """Tests create many users; the production hasher is deliberately slow."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _no_real_tmdb(settings, monkeypatch):
    """Tests never reach TMDB: give the client a dummy token and make real HTTP fail loudly.

    Tests that exercise the client replace `requests.get` themselves.
    """
    settings.TMDB_READ_ACCESS_TOKEN = "test-token"

    def _blocked(*args, **kwargs):
        raise AssertionError(f"Real HTTP request attempted in a test: {args} {kwargs}")

    monkeypatch.setattr(requests, "get", _blocked)


@pytest.fixture
def make_user(db):
    def _make_user(username):
        return get_user_model().objects.create_user(username=username, password=PASSWORD)

    return _make_user


@pytest.fixture
def owner(make_user):
    return make_user("owner")


@pytest.fixture
def shared_user(make_user):
    return make_user("friend")


@pytest.fixture
def stranger(make_user):
    return make_user("stranger")


@pytest.fixture
def make_movie(db):
    """Create a locally stored Movie (no TMDB involved)."""
    from catalog.models import Movie

    def _make_movie(tmdb_id=27205, title="Inception", **fields):
        fields.setdefault("last_fetched_at", timezone.now())
        return Movie.objects.create(tmdb_id=tmdb_id, title=title, **fields)

    return _make_movie


@pytest.fixture
def anon_client(client):
    """A Django test client with nobody signed in."""
    return client


@pytest.fixture
def owner_client(client, owner):
    """A Django test client signed in as `owner`."""
    client.force_login(owner)
    return client


@pytest.fixture
def api_client():
    """A DRF test client with no credentials."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def token_for(db):
    """Return the API token key for a user (creating it if needed)."""
    from rest_framework.authtoken.models import Token

    def _token_for(user):
        return Token.objects.get_or_create(user=user)[0].key

    return _token_for
