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
- CSS: after changing classes in templates or `*/forms.py` widget attrs, `./tools/tailwindcss.exe -i assets/tailwind/input.css -o static/css/app.css --minify` and commit `app.css`. The CLI binary is git-ignored; README has the download step.

## Conventions in use

- Templates live in the project-level `templates/` dir (`base.html` holds the navbar and TMDB attribution footer). Tailwind scans `templates/`, `*/templates/`, and `*/forms.py`.
- Form fields render inside `<fieldset class="fieldset" data-field="<name>">` with that field's errors directly below the input (tests locate errors by `data-field`).
- Entry rules: save entries through a form/`full_clean()`, never raw `.update()`. `Entry.clean()` rejects rating/date watched/times watched > 0 per field unless Watched, and clears them when the last-saved status (`_saved_status`) was Watched. The API serializer must reuse this, not reimplement it.
- Other users' objects return 404 (look up with `user=request.user` in `get_object_or_404`), never 403.
- `static/js/app.js` holds small vanilla-JS enhancements (watched-only input toggling, Clear rating); keep pages working without it.
- App URLs are namespaced (`accounts:`, `catalog:`, `library:`); data-managing views use `@login_required` (`LOGIN_URL = "accounts:login"`).
- HTMX is pinned at 2.0.11 (`static/js/htmx.min.js`) for django-htmx compatibility; the CSRF token is sent via `hx-headers` on `<body>`.
- HTMX views: the full-page template `{% include %}`s a partial from `templates/<app>/partials/`; the view returns just that partial when `request.htmx` (but the full page for `request.htmx.history_restore_request`).
- Browsing entries (library, list pages, API) goes through `library/browse.py`: `clean_params` (`q`, `status`, `genre` = TMDB genre id, `min_rating`, `decade`, `sort`, `dir`, `page`; invalid values ignored), `browse_entries` (search/filter/sort, missing values last), and `browse_context` (20 per page + controls). Pass the unfiltered, already-scoped queryset (e.g. `user=request.user`). The website renders it with `library/partials/browse.html` inside `#library-browse` (HTMX swaps with `hx-push-url`; page links use `{% querystring %}`).
- TMDB client is `catalog/tmdb.py`: every failure raises `TMDBError` with a `kind` and a user-readable `message`. Views call it as `tmdb.<function>` (so tests can monkeypatch it), catch `TMDBError`, and render the message as a DaisyUI `role="alert"` with HTTP 200 so HTMX swaps it in.
- Getting a Movie for a TMDB id always goes through `catalog.services.get_or_fetch_movie` (stored row first, TMDB only if missing; raises `TMDBError`). `_store_details` there copies TMDB details + genres onto a Movie and is meant for reuse by refresh.
- Posters: render with `{% include "partials/poster.html" with url=... title=... %}` (TMDB URL via `Movie.poster_url`, placeholder on missing or failed load).
- Duplicates rely on DB unique constraints: create inside `transaction.atomic()` and handle `IntegrityError`, rather than check-then-create.
- Tests sit in each app's `tests/` package; shared fixtures (`owner`, `shared_user`, `stranger`, `anon_client`, `owner_client`, `make_movie`) are in the root `conftest.py`. Autouse fixtures there use a fast password hasher, set a dummy TMDB token, and make any real `requests.get` fail the test; fake TMDB by monkeypatching `catalog.tmdb` functions (or `tmdb.requests.get` in client tests).
- Ad-hoc checks against the real DB: `uv run --env-file .env python manage.py shell -c "exec(open(path).read())"` (piping into `shell` doesn't work); call `django.test.utils.setup_test_environment()` before reading `response.context`, set `PYTHONIOENCODING=utf-8` before printing ★, and delete any data created in a `finally` block.

## References

- PRD (requirements, user stories, detailed rules): `prd/movie-watch-log.md`
- Implementation plan (phases, acceptance criteria): `plans/movie-watch-log.md`
- Rating-scale prototype and decision: `prototypes/rating-scale.html`
