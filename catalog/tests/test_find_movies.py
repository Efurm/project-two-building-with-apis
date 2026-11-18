from django.urls import reverse

from catalog import tmdb

INCEPTION = {
    "id": 27205,
    "title": "Inception",
    "release_date": "2010-07-15",
    "overview": "Cobb, a skilled thief who commits corporate espionage by infiltrating "
    "the subconscious of his targets, is offered a chance to regain his old life "
    "as payment for a task considered to be impossible.",
    "poster_path": "/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
}


def test_htmx_search_returns_results_partial_with_title_year_and_short_overview(
    owner_client, monkeypatch
):
    monkeypatch.setattr(tmdb, "search_movies", lambda query: {"results": [INCEPTION]})

    response = owner_client.get(reverse("catalog:find"), {"q": "inception"}, HTTP_HX_REQUEST="true")
    content = response.content.decode()

    assert response.status_code == 200
    assert "<html" not in content
    assert "Inception" in content
    assert "2010" in content
    assert "Cobb, a skilled thief" in content
    assert "considered to be impossible" not in content


def test_tmdb_failure_during_search_shows_alert_in_results_area(owner_client, monkeypatch):
    def failing_search(query):
        raise tmdb.TMDBError(
            "timeout", "TMDB did not respond within 10 seconds. Try again shortly."
        )

    monkeypatch.setattr(tmdb, "search_movies", failing_search)
    owner_client.raise_request_exception = False  # observe the response a browser would get

    response = owner_client.get(reverse("catalog:find"), {"q": "inception"}, HTTP_HX_REQUEST="true")
    content = response.content.decode()

    assert response.status_code == 200
    assert 'role="alert"' in content
    assert "TMDB did not respond within 10 seconds. Try again shortly." in content


def fake_search(results):
    calls = []

    def _search(query):
        calls.append(query)
        return {"results": results}

    _search.calls = calls
    return _search


def test_find_requires_sign_in(anon_client):
    response = anon_client.get(reverse("catalog:find"))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


def test_find_page_without_query_shows_form_and_does_not_call_tmdb(owner_client, monkeypatch):
    search = fake_search([INCEPTION])
    monkeypatch.setattr(tmdb, "search_movies", search)

    response = owner_client.get(reverse("catalog:find"))

    assert response.status_code == 200
    assert b'name="q"' in response.content
    assert search.calls == []


def test_blank_query_does_not_call_tmdb(owner_client, monkeypatch):
    search = fake_search([INCEPTION])
    monkeypatch.setattr(tmdb, "search_movies", search)

    owner_client.get(reverse("catalog:find"), {"q": "   "}, HTTP_HX_REQUEST="true")

    assert search.calls == []


def test_non_htmx_search_renders_full_page_with_results(owner_client, monkeypatch):
    monkeypatch.setattr(tmdb, "search_movies", fake_search([INCEPTION]))

    response = owner_client.get(reverse("catalog:find"), {"q": "inception"})
    content = response.content.decode()

    assert "<html" in content
    assert 'value="inception"' in content
    assert "Inception" in content


def test_search_passes_trimmed_query_to_client(owner_client, monkeypatch):
    search = fake_search([])
    monkeypatch.setattr(tmdb, "search_movies", search)

    owner_client.get(reverse("catalog:find"), {"q": "  the matrix "}, HTTP_HX_REQUEST="true")

    assert search.calls == ["the matrix"]


def test_no_results_shows_try_different_words_message(owner_client, monkeypatch):
    monkeypatch.setattr(tmdb, "search_movies", fake_search([]))

    response = owner_client.get(
        reverse("catalog:find"), {"q": "zzqqxx"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert "No movies found for “zzqqxx”" in response
    assert "Try different words" in response


def test_result_shows_tmdb_poster_with_placeholder_fallback(owner_client, monkeypatch):
    monkeypatch.setattr(tmdb, "search_movies", fake_search([INCEPTION]))

    content = owner_client.get(
        reverse("catalog:find"), {"q": "inception"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert 'src="https://image.tmdb.org/t/p/w185/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg"' in content
    assert "onerror=" in content
    assert "/static/img/poster-placeholder.svg" in content


def test_result_without_poster_or_date_uses_placeholder_and_no_year(owner_client, monkeypatch):
    movie = {
        "id": 1,
        "title": "Obscure Film",
        "release_date": "",
        "overview": "",
        "poster_path": None,
    }
    monkeypatch.setattr(tmdb, "search_movies", fake_search([movie]))

    content = owner_client.get(
        reverse("catalog:find"), {"q": "obscure"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert 'src="/static/img/poster-placeholder.svg"' in content
    assert "Obscure Film" in content
    assert "No overview available." in content
    assert "()" not in content


def test_result_text_is_html_escaped(owner_client, monkeypatch):
    movie = dict(INCEPTION, title="<script>alert(1)</script>")
    monkeypatch.setattr(tmdb, "search_movies", fake_search([movie]))

    content = owner_client.get(
        reverse("catalog:find"), {"q": "x"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content


def test_unconfigured_token_shows_alert_on_find_page(owner_client, settings):
    settings.TMDB_READ_ACCESS_TOKEN = ""

    response = owner_client.get(reverse("catalog:find"), {"q": "inception"}, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert 'role="alert"' in response.content.decode()
    assert "no TMDB access token" in response.content.decode()


def test_navbar_links_to_find_movies(owner_client):
    content = owner_client.get(reverse("library:index")).content.decode()

    assert f'href="{reverse("catalog:find")}"' in content


def test_results_already_in_library_show_in_library_others_show_save(
    owner_client, owner, stranger, make_movie, monkeypatch
):
    from library.models import Entry

    matrix = {"id": 603, "title": "The Matrix", "release_date": "1999-03-31", "overview": ""}
    Entry.objects.create(user=owner, movie=make_movie(tmdb_id=27205))
    Entry.objects.create(user=stranger, movie=make_movie(tmdb_id=603, title="The Matrix"))
    monkeypatch.setattr(tmdb, "search_movies", fake_search([INCEPTION, matrix]))

    content = owner_client.get(
        reverse("catalog:find"), {"q": "x"}, HTTP_HX_REQUEST="true"
    ).content.decode()

    assert content.count("In library ✓") == 1
    assert f'hx-post="{reverse("catalog:save", args=[603])}"' in content
    assert f'hx-post="{reverse("catalog:save", args=[27205])}"' not in content
    assert 'value="want_to_watch"' in content and 'value="watched"' in content
