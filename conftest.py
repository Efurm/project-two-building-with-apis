"""Shared pytest fixtures for the whole project."""

import pytest
from django.contrib.auth import get_user_model

PASSWORD = "correct-horse-battery-staple"


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
def anon_client(client):
    """A Django test client with nobody signed in."""
    return client


@pytest.fixture
def owner_client(client, owner):
    """A Django test client signed in as `owner`."""
    client.force_login(owner)
    return client
