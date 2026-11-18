# Movie Watch Log

A Django web app and REST API for saving movies from TMDB to a personal library,
annotating them, and organizing them into private, public, or shared lists.

- Requirements: [`prd/movie-watch-log.md`](prd/movie-watch-log.md)
- Implementation plan: [`plans/movie-watch-log.md`](plans/movie-watch-log.md)

## Setup

Requires [uv](https://docs.astral.sh/uv/). No Node.js or npm.

```sh
uv sync
cp .env.example .env        # then fill in TMDB_READ_ACCESS_TOKEN and DJANGO_SECRET_KEY
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign up.

## Tests and linting

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```

Tests never call TMDB and do not need `.env`.

## Styling (Tailwind + DaisyUI)

The built stylesheet `static/css/app.css` is committed, so the app runs without a
build step. Rebuild it only after changing classes in templates.

The build uses Tailwind's standalone CLI with the DaisyUI plugin files in
`assets/tailwind/` (`daisyui.mjs`, `daisyui-theme.mjs`, DaisyUI v5.8.1). The CLI
binary is git-ignored; download it once into `tools/`:

```sh
# Windows (Tailwind v4.3.5). For macOS/Linux pick the matching asset from
# https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.5
curl -L -o tools/tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.5/tailwindcss-windows-x64.exe
```

Then build (add `--watch` while editing templates):

```sh
./tools/tailwindcss.exe -i assets/tailwind/input.css -o static/css/app.css --minify
```

HTMX (v2.0.11) is served locally from `static/js/htmx.min.js`.

## REST API

The API (Django REST Framework) lives under `/api/` and uses the website session or a
personal token. Generate a token on the "My account" page (`/accounts/me/`), then:

```sh
TOKEN=your-token-here
BASE=http://127.0.0.1:8000/api

# List your library (same parameters as the website: q, status, genre, min_rating,
# decade, sort, dir, page; 20 per page)
curl -H "Authorization: Token $TOKEN" "$BASE/entries/?status=watched&sort=rating"

# Add a movie by TMDB id (optional: status, rating, notes, date_watched, times_watched)
curl -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json"      -d '{"tmdb_id": 603, "status": "watched", "rating": 5}' "$BASE/entries/"

# Update or delete one of your entries
curl -X PATCH -H "Authorization: Token $TOKEN" -H "Content-Type: application/json"      -d '{"notes": "Rewatch soon"}' "$BASE/entries/1/"
curl -X DELETE -H "Authorization: Token $TOKEN" "$BASE/entries/1/"
```

Entries are always private to their owner (others' entries are 404). Status and rating
follow the same rules as the website. Creating an entry for a movie that is not stored
yet needs TMDB; if TMDB is unavailable the API responds `503` with a `detail` message.

## Refreshing cached TMDB data

TMDB's terms require cached data to be refreshed at least every 6 months. Saved movies
can be refreshed one at a time with the "Refresh from TMDB" button on an entry's page, or
in bulk with:

```sh
uv run --env-file .env python manage.py refresh_movies               # older than 180 days
uv run --env-file .env python manage.py refresh_movies --older-than 30
```

Failures are reported and skipped; the stored data for those movies is unchanged.

## TMDB command-line search

```sh
uv run --env-file .env scripts/tmdb_search.py inception
```

This product uses the TMDB API but is not endorsed or certified by TMDB.
