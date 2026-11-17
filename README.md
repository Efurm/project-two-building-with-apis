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

## TMDB command-line search

```sh
uv run --env-file .env scripts/tmdb_search.py inception
```

This product uses the TMDB API but is not endorsed or certified by TMDB.
