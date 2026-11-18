"""Use the Movie Watch Log REST API from the command line.

Two commands:

    list    GET /api/entries/ with query parameters and print the matching entries.
    update  PATCH /api/entries/<id>/ to change one field, printing it before and after.

Examples (the dev server must be running: uv run --env-file .env python manage.py runserver):

    uv run --env-file .env scripts/api_client.py list --status watched --sort rating
    uv run --env-file .env scripts/api_client.py list --q heat --min-rating 4 --dir asc
    uv run --env-file .env scripts/api_client.py update 12 notes "Rewatch with friends"
    uv run --env-file .env scripts/api_client.py update 12 status watched
    uv run --env-file .env scripts/api_client.py update 12 rating 5

Requires MOVIELOG_API_TOKEN in .env (generate it on the site's "My account" page).
MOVIELOG_API_URL defaults to http://127.0.0.1:8000/api.
"""

import argparse
import os
import sys

import requests

DEFAULT_API_URL = "http://127.0.0.1:8000/api"
TIMEOUT_SECONDS = 10
STATUSES = ["want_to_watch", "watching", "watched"]
SORTS = ["added", "title", "rating", "released", "watched"]

# The user fields an entry update may change, and how to turn the command-line text
# into the JSON value the API expects. "none" clears a nullable field.
UPDATABLE_FIELDS = {
    "status": str,
    "rating": lambda text: None if text.lower() == "none" else int(text),
    "notes": str,
    "date_watched": lambda text: None if text.lower() == "none" else text,
    "times_watched": int,
}


class APIError(Exception):
    """A request to the API failed; the message is meant for the user."""


def fail(message):
    """Print an error message and exit with a non-zero status."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def get_settings():
    token = os.environ.get("MOVIELOG_API_TOKEN", "").strip()
    if not token:
        fail(
            "MOVIELOG_API_TOKEN is not set.\n"
            "  1. Start the site and open My account (/accounts/me/) to generate a token.\n"
            "  2. Add MOVIELOG_API_TOKEN=<token> to .env (see .env.example).\n"
            "  3. Run with: uv run --env-file .env scripts/api_client.py ..."
        )
    base_url = os.environ.get("MOVIELOG_API_URL", DEFAULT_API_URL).strip().rstrip("/")
    return base_url, token


def request(method, url, token, **kwargs):
    """Send one API request and return the decoded JSON body, or raise APIError."""
    try:
        response = requests.request(
            method,
            url,
            headers={"Authorization": f"Token {token}", "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
            **kwargs,
        )
    except requests.exceptions.Timeout as error:
        raise APIError(f"The API did not respond within {TIMEOUT_SECONDS} seconds.") from error
    except requests.exceptions.ConnectionError as error:
        raise APIError(
            f"Could not connect to {url}. Is the dev server running "
            "(uv run --env-file .env python manage.py runserver)?"
        ) from error
    except requests.exceptions.RequestException as error:
        raise APIError(f"Request to the API failed: {error}") from error

    try:
        body = response.json()
    except ValueError:
        body = None

    if response.status_code == 401:
        raise APIError("The API rejected the token (401). Check MOVIELOG_API_TOKEN in .env.")
    if response.status_code == 404:
        raise APIError("Not found (404). The entry does not exist or is not yours.")
    if response.status_code == 400 and isinstance(body, dict):
        problems = "; ".join(
            f"{field}: {' '.join(map(str, messages)) if isinstance(messages, list) else messages}"
            for field, messages in body.items()
        )
        raise APIError(f"The API rejected the request (400). {problems}")
    if not response.ok:
        detail = body.get("detail", "") if isinstance(body, dict) else ""
        raise APIError(f"The API returned HTTP {response.status_code}. {detail}".strip())
    if body is None:
        raise APIError("The API sent a response that was not valid JSON.")
    return body


def format_entry(entry):
    """One entry as two readable lines."""
    movie = entry["movie"]
    year = (movie.get("release_date") or "")[:4] or "year unknown"
    rating = entry["rating"]
    stars = "★" * rating + "☆" * (5 - rating) if rating else "unrated"
    status = entry["status"].replace("_", " ")
    line = f"#{entry['id']:<5} {movie['title']} ({year})  [{status}]  {stars}"
    if entry["status"] == "watched":
        line += f"  watched {entry['times_watched']}x"
        if entry["date_watched"]:
            line += f", last {entry['date_watched']}"
    notes = (entry["notes"] or "").replace("\n", " ")
    if len(notes) > 80:
        notes = notes[:80].rstrip() + "…"
    return line + (f"\n       notes: {notes}" if notes else "")


def list_entries(args, base_url, token):
    """Behavior 1: GET /api/entries/ with query parameters and print the results."""
    params = {
        "q": args.q,
        "status": args.status,
        "genre": args.genre,
        "min_rating": args.min_rating,
        "decade": args.decade,
        "sort": args.sort,
        "dir": args.dir,
        "page": args.page,
    }
    params = {key: value for key, value in params.items() if value is not None}
    body = request("GET", f"{base_url}/entries/", token, params=params)

    shown = ", ".join(f"{k}={v}" for k, v in params.items()) or "none"
    print(f"GET {base_url}/entries/   query: {shown}\n")
    if not body["results"]:
        print("No entries match these parameters.")
        return
    for entry in body["results"]:
        print(format_entry(entry))
    page = args.page or 1
    print(f"\nShowing {len(body['results'])} of {body['count']} entries (page {page}).")
    if body["next"]:
        print(f"More results: add --page {page + 1}")


def update_entry(args, base_url, token):
    """Behavior 2: PATCH one field of an entry and print it before and after."""
    try:
        value = UPDATABLE_FIELDS[args.field](args.value)
    except ValueError:
        fail(f"{args.field} must be a whole number (got {args.value!r}).")

    url = f"{base_url}/entries/{args.entry_id}/"
    before = request("GET", url, token)
    after = request("PATCH", url, token, json={args.field: value})

    print(f"PATCH {url}   {{{args.field!r}: {value!r}}}\n")
    print("Before:")
    print(format_entry(before))
    print("\nAfter:")
    print(format_entry(after))

    changed = [field for field in UPDATABLE_FIELDS if before[field] != after[field]]
    print("\nChanged fields:")
    if not changed:
        print("  (none: the entry already had that value)")
    for field in changed:
        print(f"  {field}: {before[field]!r} -> {after[field]!r}")


def build_parser():
    parser = argparse.ArgumentParser(description="Use the Movie Watch Log REST API.")
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="List your entries with query parameters.")
    list_cmd.add_argument("--q", help="Search titles and your notes.")
    list_cmd.add_argument("--status", choices=STATUSES)
    list_cmd.add_argument("--genre", type=int, help="TMDB genre id (e.g. 878 = Science Fiction).")
    list_cmd.add_argument("--min-rating", type=int, choices=range(1, 6), dest="min_rating")
    list_cmd.add_argument("--decade", type=int, help="e.g. 1990 for 1990-1999.")
    list_cmd.add_argument("--sort", choices=SORTS)
    list_cmd.add_argument("--dir", choices=["asc", "desc"])
    list_cmd.add_argument("--page", type=int)

    update_cmd = commands.add_parser("update", help="Change one field of one of your entries.")
    update_cmd.add_argument("entry_id", type=int, help="The entry id (shown by 'list').")
    update_cmd.add_argument("field", choices=list(UPDATABLE_FIELDS))
    update_cmd.add_argument("value", help='New value. Use "none" to clear rating or date_watched.')
    return parser


def main():
    # Windows consoles may not default to UTF-8; avoid crashes on stars or accented titles.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args()
    base_url, token = get_settings()
    try:
        if args.command == "list":
            list_entries(args, base_url, token)
        else:
            update_entry(args, base_url, token)
    except APIError as error:
        fail(str(error))


if __name__ == "__main__":
    main()
