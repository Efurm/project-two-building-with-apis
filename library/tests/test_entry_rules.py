import datetime
import re

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from library.models import Entry


def validation_errors(entry):
    """Run model validation and return {field: [messages]} ({} when valid)."""
    try:
        entry.full_clean()
    except ValidationError as error:
        return error.message_dict
    return {}


@pytest.mark.django_db
def test_watched_only_fields_are_rejected_per_field_unless_status_is_watched(owner, make_movie):
    entry = Entry.objects.create(user=owner, movie=make_movie())
    entry.status = Entry.Status.WATCHING
    entry.rating = 4
    entry.date_watched = datetime.date(2026, 11, 1)
    entry.times_watched = 2

    errors = validation_errors(entry)

    assert set(errors) == {"rating", "date_watched", "times_watched"}

    entry.status = Entry.Status.WATCHED
    assert validation_errors(entry) == {}


def test_changing_status_away_from_watched_in_edit_form_clears_watched_only_fields(
    owner_client, owner, make_movie
):
    entry = Entry.objects.create(
        user=owner,
        movie=make_movie(),
        status=Entry.Status.WATCHED,
        rating=4,
        date_watched=datetime.date(2026, 11, 1),
        times_watched=2,
        notes="Loved the ending.",
    )

    response = owner_client.post(
        reverse("library:entry_edit", args=[entry.pk]),
        {
            "status": Entry.Status.WATCHING,
            "rating": "4",
            "date_watched": "2026-11-01",
            "times_watched": "2",
            "notes": "Loved the ending.",
        },
        HTTP_HX_REQUEST="true",
    )

    entry.refresh_from_db()
    assert response.status_code == 200
    assert entry.status == Entry.Status.WATCHING
    assert entry.rating is None
    assert entry.date_watched is None
    assert entry.times_watched == 0
    assert entry.notes == "Loved the ending."


def field_block(html, name):
    """The HTML of the form-field wrapper marked data-field="<name>" (None if absent)."""
    match = re.search(rf'<fieldset[^>]*data-field="{name}".*?</fieldset>', html, re.S)
    return match.group(0) if match else None


def test_invalid_htmx_save_returns_form_with_error_next_to_field_and_saves_nothing(
    owner_client, owner, make_movie
):
    entry = Entry.objects.create(user=owner, movie=make_movie(), notes="Original notes.")

    response = owner_client.post(
        reverse("library:entry_edit", args=[entry.pk]),
        {
            "status": Entry.Status.WANT_TO_WATCH,
            "rating": "4",
            "date_watched": "",
            "times_watched": "0",
            "notes": "Changed notes.",
        },
        HTTP_HX_REQUEST="true",
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert 'data-testid="entry-form"' in html
    rating_block = field_block(html, "rating")
    assert rating_block is not None
    assert "You can rate a movie only after marking it Watched." in rating_block
    assert "You can rate a movie only after marking it Watched." not in field_block(html, "status")
    assert "Changed notes.</textarea>" in field_block(html, "notes")

    entry.refresh_from_db()
    assert entry.rating is None
    assert entry.notes == "Original notes."
