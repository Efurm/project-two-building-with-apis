# CLAUDE.md

Movie Watch Log: a Django web app and REST API where signed-in users save movies from TMDB to a personal library, annotate them, and organize them into private, public, or shared lists.

## Stack

- Python, Django, Django REST Framework, SQLite.
- Package manager: uv. Lint/format: Ruff. Tests: pytest + pytest-django.
- Styling: Tailwind CSS + DaisyUI via Tailwind's standalone CLI (no Node.js/npm); the built stylesheet is committed.
- Interactivity: HTMX served as a local static file (not a CDN), plus `django-htmx`.
- Secrets (TMDB Read Access Token, Django secret key) live in the git-ignored `.env`, loaded with uv's `--env-file` option.

## Architecture decisions

- Settings package `config`; apps `accounts` (sign-up, auth, API token), `catalog` (everything that talks to TMDB), `library` (entries, lists, sharing, DRF API). Django's default User model.
- Only search, save, and refresh call TMDB, through a single client module. All other pages and API reads use local data only and must work with TMDB unreachable.
- TMDB failures become specific, user-readable errors; saved data is never affected.
- Entry status/rating rules are defined once on the model and enforced by both the website form and the API serializer.
- List visibility rules live in one place (a `MovieList` queryset method plus a matching DRF object permission), shared by website and API. Lists a viewer can't see return 404, not 403.
- Tests never make real TMDB network calls; the client is always faked.

## Commands (verified)

- Run: `uv run --env-file .env python manage.py migrate` then `... runserver`
- Test: `uv run pytest` (no `.env` needed; settings fall back to a dev-only secret key)
- Lint/format: `uv run ruff check .` and `uv run ruff format .`
- CSS: after changing template classes, `./tools/tailwindcss.exe -i assets/tailwind/input.css -o static/css/app.css --minify` and commit `app.css`. The CLI binary is git-ignored; README has the download step.

## Conventions in use

- Templates live in the project-level `templates/` dir (`base.html` holds the navbar and TMDB attribution footer). Tailwind scans `templates/` and `*/templates/`.
- App URLs are namespaced (`accounts:`, `library:`); data-managing views use `@login_required` (`LOGIN_URL = "accounts:login"`).
- HTMX is pinned at 2.0.11 (`static/js/htmx.min.js`) for django-htmx compatibility; the CSRF token is sent via `hx-headers` on `<body>`.
- Tests sit in each app's `tests/` package; shared fixtures (`owner`, `shared_user`, `stranger`, `anon_client`, `owner_client`) are in the root `conftest.py`.

## References

- PRD (requirements, user stories, detailed rules): `prd/movie-watch-log.md`
- Implementation plan (phases, acceptance criteria): `plans/movie-watch-log.md`
- Rating-scale prototype and decision: `prototypes/rating-scale.html`
