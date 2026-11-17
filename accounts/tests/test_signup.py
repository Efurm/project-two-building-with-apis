import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_signup_creates_account_signs_in_and_lands_on_library(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "newviewer",
            "password1": "a-long-unusual-passphrase-42",
            "password2": "a-long-unusual-passphrase-42",
        },
        follow=True,
    )

    assert get_user_model().objects.filter(username="newviewer").exists()
    assert response.redirect_chain[-1][0] == reverse("library:index")
    assert response.context["user"].is_authenticated
    assert response.context["user"].username == "newviewer"
