import pytest
import requests

from catalog import tmdb


def fake_response(status, body=b"{}"):
    response = requests.Response()
    response.status_code = status
    response._content = body
    return response


def raises(exc):
    def _get(*args, **kwargs):
        raise exc

    return _get


def returns(response):
    def _get(*args, **kwargs):
        return response

    return _get


@pytest.mark.parametrize(
    ("fake_get", "kind", "phrase"),
    [
        (raises(requests.exceptions.Timeout()), "timeout", "did not respond within 10 seconds"),
        (raises(requests.exceptions.ConnectionError()), "connection", "Could not connect to TMDB"),
        (returns(fake_response(401)), "auth", "TMDB rejected"),
        (returns(fake_response(429)), "rate_limit", "rate limit"),
        (
            returns(fake_response(500, b'{"status_message": "Internal error."}')),
            "http",
            "TMDB returned HTTP 500. Internal error.",
        ),
        (returns(fake_response(200, b"<html>not json</html>")), "invalid_json", "not valid JSON"),
    ],
    ids=["timeout", "connection", "401", "429", "500", "invalid-json"],
)
def test_each_failure_becomes_a_specific_readable_error(monkeypatch, fake_get, kind, phrase):
    monkeypatch.setattr(tmdb.requests, "get", fake_get)

    with pytest.raises(tmdb.TMDBError) as caught:
        tmdb.search_movies("inception")

    assert caught.value.kind == kind
    assert phrase in caught.value.message


def test_other_request_failures_become_a_request_error(monkeypatch):
    monkeypatch.setattr(tmdb.requests, "get", raises(requests.exceptions.TooManyRedirects("loop")))

    with pytest.raises(tmdb.TMDBError) as caught:
        tmdb.search_movies("inception")

    assert caught.value.kind == "request"
    assert "Request to TMDB failed" in caught.value.message


@pytest.mark.parametrize("token", ["", "   "])
def test_missing_token_is_reported_without_calling_tmdb(settings, token):
    settings.TMDB_READ_ACCESS_TOKEN = token  # requests.get is blocked; a call would fail loudly

    with pytest.raises(tmdb.TMDBError) as caught:
        tmdb.search_movies("inception")

    assert caught.value.kind == "not_configured"
    assert "no TMDB access token" in caught.value.message


def test_search_sends_bearer_token_query_and_timeout(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return fake_response(200, b'{"results": []}')

    monkeypatch.setattr(tmdb.requests, "get", fake_get)

    assert tmdb.search_movies("inception") == {"results": []}
    url, kwargs = calls[0]
    assert url == "https://api.themoviedb.org/3/search/movie"
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["params"]["query"] == "inception"
    assert kwargs["timeout"] == tmdb.TIMEOUT_SECONDS


def test_poster_url_builds_cdn_url_or_none():
    assert tmdb.poster_url("/abc.jpg") == "https://image.tmdb.org/t/p/w185/abc.jpg"
    assert tmdb.poster_url(None) is None
    assert tmdb.poster_url("") is None
