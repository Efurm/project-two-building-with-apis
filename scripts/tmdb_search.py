"""Search TMDB for movies from the command line.

Usage:
    uv run --env-file .env scripts/tmdb_search.py inception
    uv run --env-file .env scripts/tmdb_search.py        # prompts for a search

Requires TMDB_READ_ACCESS_TOKEN in .env (see .env.example).
"""

import os
import sys

import requests

SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MAX_RESULTS = 5
OVERVIEW_LENGTH = 100
TIMEOUT_SECONDS = 10


def fail(message):
    """Print an error message and exit with a non-zero status."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def get_token():
    token = os.environ.get("TMDB_READ_ACCESS_TOKEN", "").strip()
    if not token:
        fail(
            "TMDB_READ_ACCESS_TOKEN is not set.\n"
            "  1. Copy .env.example to .env and paste your TMDB Read Access Token.\n"
            "  2. Run with: uv run --env-file .env scripts/tmdb_search.py <search>"
        )
    return token


def get_query():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Search for a movie: ")
    query = query.strip()
    if not query:
        fail("Search phrase cannot be blank.")
    return query


def search_movies(query, token):
    """Call TMDB's movie search and return the decoded JSON body."""
    try:
        response = requests.get(
            SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            params={"query": query, "include_adult": "false", "language": "en-US", "page": 1},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        fail(f"TMDB did not respond within {TIMEOUT_SECONDS} seconds. Try again shortly.")
    except requests.exceptions.ConnectionError:
        fail("Could not connect to TMDB. Check your internet connection.")
    except requests.exceptions.RequestException as error:
        fail(f"Request to TMDB failed: {error}")

    if response.status_code == 401:
        fail("TMDB rejected the token (401). Check TMDB_READ_ACCESS_TOKEN in .env "
             "- it should be the long 'API Read Access Token', not the short API key.")
    if response.status_code == 429:
        fail("TMDB rate limit reached (429). Wait a few seconds and try again.")
    if not response.ok:
        try:
            detail = response.json().get("status_message", "")
        except ValueError:
            detail = ""
        fail(f"TMDB returned HTTP {response.status_code}. {detail}".strip())

    try:
        return response.json()
    except ValueError:
        fail("TMDB sent a response that was not valid JSON.")


def format_movie(number, movie):
    title = movie.get("title") or "(untitled)"
    year = (movie.get("release_date") or "")[:4] or "year unknown"
    rating = movie.get("vote_average") or 0
    overview = (movie.get("overview") or "No overview available.").replace("\n", " ")
    if len(overview) > OVERVIEW_LENGTH:
        overview = overview[:OVERVIEW_LENGTH].rstrip() + "…"
    return (
        f"{number}. {title} ({year})  ★ {rating:.1f}  [id {movie.get('id')}]\n"
        f"   {overview}"
    )


def main():
    # Windows consoles may not default to UTF-8; avoid crashes on ★ or accented titles.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    token = get_token()
    query = get_query()
    data = search_movies(query, token)

    movies = data.get("results", [])
    if not movies:
        print(f'No movies found for "{query}". Try a different spelling or fewer words.')
        return

    total = data.get("total_results", len(movies))
    print(f'\nTMDB results for "{query}":\n')
    for number, movie in enumerate(movies[:MAX_RESULTS], start=1):
        print(format_movie(number, movie))
        print()
    print(f"Showing {min(MAX_RESULTS, len(movies))} of {total} results.")


if __name__ == "__main__":
    main()
