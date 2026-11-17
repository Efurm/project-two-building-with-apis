# Plan: Movie Watch Log

> Source PRD: `prd/movie-watch-log.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Django + Django REST Framework + SQLite, managed with uv. Ruff for lint/format. pytest + pytest-django (dev dependencies). Tailwind CSS + DaisyUI built by the Tailwind standalone CLI (no Node/npm); the built stylesheet is committed. HTMX served as a local static file, plus `django-htmx`. Secrets (`TMDB_READ_ACCESS_TOKEN`, Django secret key) come from the git-ignored `.env` via `uv run --env-file .env`.
- **Project layout**: settings package `config`; apps `accounts`, `catalog`, `library`. Django's default User model.
- **Owning apps**:
  - **accounts**: sign-up, login/logout, "My account" (API token). No models of its own; uses DRF `authtoken`.
  - **catalog**: `Genre`, `Movie`, the TMDB client module, the shared "get or fetch movie" service, Find movies, save, refresh, and the refresh management command.
  - **library**: `Entry`, `MovieList`, `ListItem`, library/entry/list/profile/"Shared with me" pages, and the DRF API.
- **Models**:
  - `Genre`: TMDB genre id, name.
  - `Movie`: one row per TMDB id (unique); title, original title, release date (nullable), overview, runtime (nullable), vote average, poster path (nullable), genres (M2M → Genre), last-fetched timestamp. Stores poster path only; full URLs built at render time.
  - `Entry`: user (FK), movie (FK), status (Want to watch / Watching / Watched, default Want to watch), rating (1–5, nullable), notes, date watched (nullable), times watched (non-negative), created/updated. Unique on (user, movie). Cross-field rule defined once on the model: rating, date watched, and times watched > 0 only when Watched; cleared when status leaves Watched.
  - `MovieList`: owner (FK → User), name, visibility (Private / Public / Shared, default Private), `shared_with` (M2M → User), timestamps.
  - `ListItem`: list (FK), entry (FK), date added; unique on (list, entry); ordered by date added.
  - Delete behavior: Entry → cascades ListItems. MovieList → cascades ListItems, never Entries. Orphaned Movies are kept.
- **URLs** (website):
  - `/` → redirects to the library
  - `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/me/`
  - `/find/` — TMDB search (results swapped in via HTMX)
  - `/library/` — library browse
  - `/library/entries/<pk>/` — entry page
  - `/lists/`, `/lists/<pk>/` — lists index and list detail
  - `/u/<username>/` — profile (public lists)
  - `/shared/` — "Shared with me"
- **URLs** (API): `/api/entries/`, `/api/entries/<pk>/`, `/api/lists/`, `/api/lists/<pk>/`, `/api/lists/<pk>/items/`, `/api/lists/<pk>/items/<item_pk>/`
- **Identifiers**: entries and lists by pk; profiles by username.
- **Auth**: website uses Django session auth; data-managing pages require login. Public lists and profile pages are anonymous-readable. API uses session + DRF token authentication.
- **Visibility (single source of truth)**: a `MovieList` queryset method returning lists visible to a given user (anonymous included) plus a matching DRF object permission for writes. Used by both website and API. Invisible lists return 404, not 403. Libraries (entries) are always owner-only.
- **TMDB boundary**: only search, save (fetching an unstored movie), and refresh call TMDB, all through one client module with a timeout that maps failures to specific messages (timeout, connection failure, 401, 429, other HTTP error, invalid JSON) carried over from `scripts/tmdb_search.py`. Everything else uses local data only. Tests always fake the TMDB client; no real network in tests.
- **HTMX convention**: views return a full page for normal requests and a partial for HTMX requests. Browse parameters (search, filters, sort, page) live in the URL query string and are pushed to browser history.

---

## Phase 1: Skeleton and accounts

**User stories**: 1, 2, 4

### What to build

Stand up the Django project (`config` + `accounts`, `catalog`, `library`), the dev tooling (ruff, pytest + pytest-django, `.env` loading of the secret key and TMDB token), the Tailwind/DaisyUI standalone build with committed CSS, and the local HTMX static file. Create a base layout with a navbar (Find movies, Library, Lists, Shared with me, account links) and a footer with TMDB attribution. A visitor can sign up with username/password, log in, and log out. Visiting any data-managing page while signed out redirects to login. After sign-in, the user lands on an empty library page.

### Acceptance criteria

- [ ] `uv run --env-file .env python manage.py runserver` starts the site with styled DaisyUI pages and no CDN dependencies for CSS or HTMX.
- [ ] A visitor can sign up, is signed in, and sees an empty library page.
- [ ] Login and logout work; logout returns the user to a signed-out state.
- [ ] Signed-out requests to `/library/` (and other managing pages) redirect to `/accounts/login/` with a `next` parameter.
- [ ] TMDB attribution is visible on every page.
- [ ] `uv run ruff check` and `uv run ruff format --check` pass; `uv run pytest` runs with shared fixtures (owner, shared user, stranger, anonymous/authenticated clients) and passing account tests.
- [ ] The Tailwind build command and how to rerun it are documented in the README.

---

## Phase 2: Find movies (search only)

**User stories**: 5, 6, 7, 12, 13

### What to build

Add the TMDB client module and the `/find/` page. The user submits a search (Enter or button, not as-you-type) and an HTMX request swaps in a results grid showing poster, title, year, and a short overview. An empty result set shows a "no movies found" message. Every TMDB failure mode shows a specific DaisyUI alert inside the results area instead of a broken page.

### Acceptance criteria

- [ ] `/find/` requires sign-in and shows a search form.
- [ ] Submitting a search swaps in results without a full page reload; a non-HTMX request renders the full page with results.
- [ ] Each result shows poster (with placeholder on load failure), title, year, and truncated overview.
- [ ] Zero results show a clear "try different words" message.
- [ ] Timeout, connection failure, 401, 429, other HTTP errors, and invalid JSON each produce a distinct, user-readable alert (messages based on the console script).
- [ ] Tests cover the client's error mapping and the page's success, empty, and each failure case using a fake TMDB client.

---

## Phase 3: Save to library and basic library page

**User stories**: 8, 9, 10, 11, 14, 25, 33

### What to build

Add `Genre`, `Movie`, and `Entry` and the shared "get or fetch movie" service. Each search result gets a Save button with a status dropdown ("Want to watch" / "Watched"); saving creates the Movie (with genres, copied from TMDB details) if needed and an Entry for the user, then swaps the button to "In library ✓". Results already in the user's library show "In library ✓" from the start. Duplicates are refused. Saving a movie that is already stored locally works even when TMDB is down. `/library/` shows the user's entries as cards from local data only, with poster placeholders.

### Acceptance criteria

- [ ] Saving a new movie creates a `Movie` (with genres and last-fetched timestamp) and an `Entry` with the chosen status; the button swaps to "In library ✓".
- [ ] Search results for movies already in the user's library show "In library ✓" instead of Save.
- [ ] Saving the same movie twice does not create a second entry (enforced by the unique constraint and handled gracefully).
- [ ] With TMDB failing, saving a movie already stored as a `Movie` still succeeds; saving an unstored movie shows a provider-unavailable alert.
- [ ] `/library/` lists only the signed-in user's entries and renders with TMDB fully unavailable.
- [ ] Posters that fail to load show a placeholder image.
- [ ] Tests cover the get-or-fetch service (stored, fetched, failed), duplicate prevention, and library rendering with no TMDB access.

---

## Phase 4: Entry page and in-place editing

**User stories**: 15, 16, 17, 18, 19, 20, 21, 22, 23

### What to build

Add `/library/entries/<pk>/` showing stored movie details (poster with fallback, overview, runtime, genres, release date, score) and the user's data. An Edit button swaps in the entry form via HTMX; Save posts it and swaps back the updated panel, or the form with field-level errors. The form uses the DaisyUI star rating (1–5 whole stars with a clear option) that is disabled unless status is Watched. The cross-field rule lives on the model and is enforced by the form; changing status away from Watched clears rating, date watched, and times watched. Each library card gets a status control that updates in place.

### Acceptance criteria

- [ ] Entry pages are visible only to the entry's owner; others get 404.
- [ ] Edit/Save happen in place via HTMX; non-HTMX requests get full pages.
- [ ] Status choices are Want to watch, Watching, Watched; rating is 1–5 or empty.
- [ ] Saving a rating, date watched, or times watched > 0 with a non-Watched status shows errors next to the relevant fields.
- [ ] Changing status away from Watched clears rating, date watched, and times watched.
- [ ] Plain-text notes save and display (escaped, not rendered as markup).
- [ ] The status control on a library card updates the entry and the card without a full reload.
- [ ] Tests cover the model rule, form validation/clearing, owner-only access, and HTMX vs full responses.

---

## Phase 5: Library browsing

**User stories**: 26, 27, 28, 29, 30, 31, 32

### What to build

Add search, filtering, sorting, and pagination to `/library/`, all on local data. Search matches movie title and the user's notes. Filters: status, genre, minimum stars, release decade. Sorts: date added, title, rating, release date, date watched — ascending or descending — with unrated entries last in either rating direction. 20 entries per page. All parameters live in the query string; changing any control swaps the results via HTMX and pushes the URL so bookmarks and the back button work. Build the browse logic so it can be reused for list detail pages and the API.

### Acceptance criteria

- [ ] Search finds entries by title or notes text, case-insensitively.
- [ ] Each filter narrows results correctly, and filters combine.
- [ ] Each sort works in both directions; unrated entries appear last in both rating directions.
- [ ] Pages contain at most 20 entries, with working page navigation.
- [ ] Changing a control updates results without a full reload and updates the browser URL; loading that URL directly reproduces the same view.
- [ ] Invalid parameter values are ignored or defaulted, never errors.
- [ ] Tests cover search, each filter, each sort (including unrated-last), and pagination boundaries.

---

## Phase 6: Refresh from TMDB

**User stories**: 34, 35, 36

### What to build

Add a "Refresh from TMDB" HTMX action on the entry page that refetches the movie's details, updates the `Movie` and its genres and last-fetched timestamp, and shows a success alert. On failure, stored data is untouched and an alert explains why. Add a `refresh_movies` management command that refreshes movies whose last-fetched timestamp is older than `--older-than` days (default 180) and reports successes and failures.

### Acceptance criteria

- [ ] Refresh updates stored movie fields, genres, and the last-fetched timestamp, and shows a success alert.
- [ ] A failed refresh leaves the stored movie unchanged and shows the specific failure message.
- [ ] `python manage.py refresh_movies` refreshes only movies older than 180 days by default; `--older-than N` changes the threshold.
- [ ] The command continues past individual failures and prints a summary.
- [ ] Tests cover refresh success/failure and the command's selection and summary with a fake client.

---

## Phase 7: Named lists (owner only)

**User stories**: 24, 37, 38, 39, 40, 41, 42, 43

### What to build

Add `MovieList` and `ListItem`. At `/lists/` the user creates, renames, and deletes lists (all Private for now). From an entry or list page the user adds and removes their own entries; the same entry can be in multiple lists. `/lists/<pk>/` shows the list's entries with each entry's status, rating, and notes, using the library's search/filter/sort/pagination behavior scoped to that list. Deleting a list never deletes entries. Deleting an entry is now available on the entry page behind a confirmation modal that states how many lists it will be removed from.

### Acceptance criteria

- [ ] Users can create, rename, and delete their lists; deleting a list leaves its entries in the library.
- [ ] Users can add an entry to a list once (no duplicates) and remove it; an entry can be in several lists.
- [ ] Attempts to add another user's entry to a list are refused.
- [ ] The list detail page supports the same search, filter, sort, pagination, and URL behavior as the library.
- [ ] List detail shows each entry's status, rating, and notes.
- [ ] Entry delete shows a confirmation with the correct list count and, once confirmed, removes the entry and its list items.
- [ ] Tests cover list CRUD, membership rules, cascade behavior, and the delete count.

---

## Phase 8: Visibility and sharing (website)

**User stories**: 44, 45, 46, 47, 48, 49, 50, 51

### What to build

Add list visibility (Private / Public / Shared) and `shared_with` management by username, with an error for unknown usernames. Implement the single visibility rule (queryset method + matching object permission) and route all list views through it. Public lists and `/u/<username>/` (the user's public lists) are viewable without signing in. `/shared/` lists lists others have shared with the signed-in user. Lists a viewer can't see return 404; non-owners never see or reach edit, add, remove, or delete controls.

### Acceptance criteria

- [ ] The owner can set visibility and add/remove `shared_with` usernames; unknown usernames show a form error.
- [ ] Anonymous visitors can view public lists and `/u/<username>/`; profile pages show only public lists.
- [ ] `/shared/` shows exactly the lists shared with the signed-in user.
- [ ] Private lists, and Shared lists for non-recipients, return 404.
- [ ] Non-owners get 404 (or are refused) on every list write action, and no write controls render for them.
- [ ] The library and entry pages remain owner-only regardless of list visibility.
- [ ] A parametrized test matrix covers viewer (owner, shared user, stranger, anonymous) × visibility (private, public, shared) × action (read, write) on the website.

---

## Phase 9: API token and entries API

**User stories**: 3, 52, 53, 54, 55, 56, 57

### What to build

Add DRF token auth and the `/accounts/me/` page where a user generates or regenerates their API token. Add the entries resource at `/api/entries/`, limited to the requester's own entries, supporting list (with the same search/filter/sort/page parameters as the library, 20 per page), create (by TMDB id plus optional user fields, using the shared get-or-fetch service), retrieve, full and partial update, and delete (204, cascading list items). Responses include nested stored movie details. The serializer enforces the same cross-field rules as the website form. Create returns 503 with a `detail` message when TMDB is needed and unavailable, and rejects movies already in the library.

### Acceptance criteria

- [ ] "My account" generates a token and regenerating invalidates the old one.
- [ ] The API accepts both session and `Authorization: Token <key>` authentication; unauthenticated entry requests are refused.
- [ ] Listing returns only the requester's entries and honors the library's browse parameters and page size.
- [ ] Create by TMDB id works for stored and unstored movies; returns 503 with `detail` when TMDB is required and fails; rejects duplicates.
- [ ] Update/partial update enforce the status/rating/date rules and clearing behavior identically to the website.
- [ ] Other users' entries return 404 for read, update, and delete.
- [ ] Delete returns 204 and removes the entry's list items.

---

## Phase 10: Lists API

**User stories**: 58, 59, 60, 61, 62

### What to build

Add the lists resource at `/api/lists/` and nested items at `/api/lists/<pk>/items/`, both using the shared visibility queryset and object permission. Listing returns lists visible to the requester, with filters for "shared with me" and owner username. Writable fields are name, visibility, and `shared_with` as usernames (unknown usernames rejected). Items can be listed, added by entry id (own entries only), and removed. Anonymous clients get read-only access to public lists and their items. Invisible lists return 404; writes on others' lists are refused.

### Acceptance criteria

- [ ] Authenticated users can create, update, and delete their lists, including visibility and `shared_with` usernames; unknown usernames return a validation error.
- [ ] Listing returns exactly the requester's visible lists; the shared-with-me and owner-username filters mirror the website pages.
- [ ] Items can be added (own entries only, no duplicates) and removed by the owner.
- [ ] Anonymous clients can read public lists and their items and cannot write anything.
- [ ] Invisible lists return 404; non-owner writes are refused.
- [ ] The parametrized visibility matrix is extended to the API surface, so website and API are verified against the same rules.
