"""The only module that talks to TMDB.

Every request goes through here with a timeout, and every failure is turned
into a `TMDBError` with a user-readable message.
"""

import requests
from django.conf import settings

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
TIMEOUT_SECONDS = 10


def poster_url(poster_path, size="w185"):
    """Full URL for a TMDB poster path, or None when the movie has no poster."""
    if not poster_path:
        return None
    return f"{IMAGE_BASE}/{size}{poster_path}"


class TMDBError(Exception):
    """A TMDB request failed. `kind` names the failure; `message` is shown to users."""

    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind
        self.message = message


def _get(path, params):
    """GET a TMDB endpoint and return decoded JSON, or raise TMDBError."""
    token = (settings.TMDB_READ_ACCESS_TOKEN or "").strip()
    if not token:
        raise TMDBError(
            "not_configured",
            "This site has no TMDB access token configured, so it cannot reach TMDB. "
            "This is not your fault.",
        )
    try:
        response = requests.get(
            f"{API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout as error:
        raise TMDBError(
            "timeout",
            f"TMDB did not respond within {TIMEOUT_SECONDS} seconds. Try again shortly.",
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise TMDBError(
            "connection",
            "Could not connect to TMDB. It may be down, or this site may be offline. "
            "Try again later.",
        ) from error
    except requests.exceptions.RequestException as error:
        raise TMDBError("request", f"Request to TMDB failed: {error}") from error

    if response.status_code == 401:
        raise TMDBError(
            "auth",
            "TMDB rejected this site's access token (401). "
            "The site's TMDB configuration needs fixing; this is not your fault.",
        )
    if response.status_code == 429:
        raise TMDBError(
            "rate_limit", "TMDB rate limit reached (429). Wait a few seconds and try again."
        )
    if not response.ok:
        try:
            detail = response.json().get("status_message", "")
        except ValueError:
            detail = ""
        raise TMDBError("http", f"TMDB returned HTTP {response.status_code}. {detail}".strip())

    try:
        return response.json()
    except ValueError as error:
        raise TMDBError("invalid_json", "TMDB sent a response that was not valid JSON.") from error


def search_movies(query):
    """Search TMDB movies by title and return the decoded JSON body."""
    return _get(
        "/search/movie",
        {"query": query, "include_adult": "false", "language": "en-US", "page": 1},
    )
