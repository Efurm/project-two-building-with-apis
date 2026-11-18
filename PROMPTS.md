# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-17 — Implemented Phase 8 (list visibility and sharing on the website) with TDD

### Prompts
1. `/implement phase 8`
2. `yes` (approved three TDD behaviors and the design: `visible_to(user)` as the single visibility rule; viewers who aren't the owner can't change a list they can see; sharing with an unknown username shows an error and shares with nobody)
3. `yes pass it` (approved the RED `visible_to` test, including that `shared_with` only counts while the list is Shared)
4. `yes` (moved on to behavior 2)
5. `yes pass it` (approved the RED non-owner write test: 7 write routes × 2 viewers × Public or Shared)
6. `yes` (moved on to behavior 3)
7. `yes pass it` (approved the RED unknown-username test and its exact message)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **Migration `0003_movielist_visibility`:** adds `visibility` (Private, Public or Shared, default Private) and `shared_with` (many-to-many to User, `related_name="shared_lists"`).
  - **`MovieList.objects.visible_to(user)`:** the single rule. It returns your own lists, every Public list, and Shared lists you're named on. Anonymous visitors get Public only. It uses a subquery, so no list appears twice.
  - **Owner-only sharing endpoints:** `POST /lists/<pk>/visibility/`, `/share/` (`ShareForm`: unknown usernames and your own are rejected with an error next to the field) and `/share/<user_pk>/remove/`. They all return the `lists/partials/sharing.html` panel (visibility radios that save on change, a help text, recipients with ✕, and the username form). Without HTMX they redirect to the list with messages.
  - **List page `/lists/<pk>/`:** now reads through `visible_to`, so it no longer requires sign-in, and lists you can't see return 404. Owners get the header, sharing panel and remove buttons. Other viewers get a "A public/shared list by X" header and read-only cards showing the owner's status, stars and notes, without links to the entry page.
  - **New pages:** a profile `/u/<username>/` (`profile`, works signed out, shows only that user's Public lists) and `/shared/` (`shared`, sign-in required, lists shared with you that are currently Shared, with their owners).
  - **Other changes:** visibility badges on the lists index (with the recipient count), and navbar links to "Shared with me" and your own profile. The lists index now counts with `distinct=True`.
  - **Checks:** 225 tests pass (3 TDD plus the website read matrix of 4 viewers × 3 visibilities × full page or HTMX, viewer-only rendering, owner controls, entries staying owner-only inside a public list, profile, an unknown profile, shared-with-me filtering and sign-in, setting visibility with its help text, an invalid visibility, share and unshare, sharing twice or with yourself, the non-HTMX share error, index badges and navbar links). Ruff is clean, no migrations are missing, the CSS was rebuilt and `0003` is applied locally.
  - **Live check on the real database:** the private, shared and public access matrix, the unknown-username error, the friend's "Shared with me" page, the friend's write attempt giving 404, the public profile and the owner-only entry page all behaved as expected. The data was cleaned up.
- **Deviations:** The user approved the design, all three behaviors and the RED tests without changes. The agent's own choices:
  - **URLs:** `/u/<username>/` and `/shared/` have top-level names (`profile`, `shared`) whose views live in `library/list_views.py`.
  - **Rules:** sharing with yourself is rejected; sharing with someone already on the list does nothing; the share form appears only while the list is Shared; usernames stay in `shared_with` when the list is made Private, but no longer count.
  - **Pages:** the profile shows `visible_to(AnonymousUser())` filtered by owner, and "Shared with me" shows `visible_to(user)` filtered to Shared and excluding your own lists, so both come from the single rule.
  - **Navbar:** your username in the navbar now links to your profile.
- **Sideways:**
  - The behavior-3 panel template linked to the `profile` URL before that URL existed. The test passed only because it rendered a Shared list. This was flagged in the GREEN summary and fixed straight away by building the profile page.
  - Counting `items` and `shared_with` in one query would have multiplied the counts; it was caught while writing the view and fixed with `distinct=True`.
  - The Phase 7 test `test_lists_pages_require_sign_in` failed, as expected, because list pages no longer require sign-in. It was rewritten: `/lists/` still requires sign-in, and a Private list is 404 for anonymous visitors.
  - Ruff's formatter split lines that were too long in the new tests (a mechanical change, including in the approved behavior-2 test).
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser, so the radio auto-save and panel swaps weren't checked visually.
  - `CLAUDE.md` was not updated in this session.

## 2026-11-17 — Logged the Phase 7 session and updated CLAUDE.md with Phase 7 conventions

### Prompts
1. `log the session to PROMPTS.md, update CLAUDE.md, then commit and push`

### Summary
- **Outcome:** Added this entry. Updated the "Conventions in use" section of `CLAUDE.md` with what Phase 7 established and tested:
  - the `lists:` namespace, and that its routes live in the `library` app (`list_urls.py`, `list_views.py`);
  - the list model rules: `ListItem` is unique per list and entry, deletes remove only memberships, and only your own entries can be added (looked up with `user=request.user`, and the API must do the same); `visibility` and `shared_with` are still to come in Phase 8;
  - the confirmation-modal pattern: `hx-get` into `#modal`, a redirect with a message (`HttpResponseClientRedirect` for HTMX), and full-page fallbacks;
  - the browse partial's optional `card_template` and `empty_message`;
  - a workflow note that Git Bash heredocs break on non-ASCII text, so files containing it should be written with the Write and Edit tools.

  Committed and pushed together with this entry.
- **Deviations:** None. Only conventions and lessons already seen in this project were added.
- **Sideways:** The Phase 7 entry was written before its commit and push, so it doesn't record that Phase 7 was committed as `54fb65a` and pushed to `origin/main`; it's noted here instead. That entry also said `CLAUDE.md` had not been updated, and this entry fixes that.

## 2026-11-17 — Implemented Phase 7 (named lists, owner only) with TDD

### Prompts
1. `/implement phase 7`
2. `yes` (approved three TDD behaviors: only your own entries can be added to your lists; deleting a list removes its items but keeps the entries; the entry-delete confirmation counts lists, and confirming deletes the entry and its items)
3. `yes pass it` (approved the RED own-entries-only test)
4. `yes` (moved on to behavior 2)
5. `yes pass it` (approved the RED delete-list test)
6. `yes` (moved on to behavior 3)
7. `yes pass it` (approved the RED entry-delete count test)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **Models and migration `0002_movielist_listitem`:** `MovieList` has an owner, name, timestamps and `entries` linked through `ListItem`. `ListItem` has a list, an entry and `added_at`, a list can hold an entry only once, and deleting either side removes only the item.
  - **Views in `library/list_views.py`, under `/lists/` (`lists:` namespace):**
    - an index with a create form and movie counts for each list;
    - a list page reusing the shared browse block, limited to that list, with cards showing status, stars, notes and "Remove from list" (the card disappears through `hx-swap="delete"`);
    - an inline HTMX rename;
    - delete with a DaisyUI confirmation modal and `HX-Redirect`;
    - add and remove item endpoints.

    Every lookup is limited to the requester (`_own_list`, `_own_entry`), so other users' lists and entries return 404.
  - **Entry page:** an "In my lists" panel (remove buttons and an "Add to list" dropdown, no JavaScript needed), plus a "Delete from library" modal that says how many lists the entry is in.
  - **Supporting changes:**
    - the browse partial takes an optional `card_template`;
    - `base.html` has a "Lists" navbar link and a `#modal` slot;
    - the new models are registered in the admin.
  - **Checks:** 155 tests pass (3 TDD plus ordinary tests for the index and counts, create and rename with validation, the delete confirmation, `HX-Redirect`, duplicate adds being ignored, an entry in several lists, removal from either page, the list page's contents, browse settings and empty state, the entry-page panel, entry delete without lists and with the non-HTMX message, 404s for seven list routes and entry delete, sign-in, and the navbar link). Ruff is clean, no migrations are missing, and the CSS was rebuilt. A live check on the real database exercised create, add (including a refused foreign entry), the list page, rename, entry delete and list delete, and the data was cleaned up.
- **Deviations:** The user approved all three behaviors and RED tests without changes. The agent's own choices:
  - **Scope:** `visibility` and `shared_with` were left for Phase 8, because the plan says lists are private-only in this phase. The PRD's model includes them, so Phase 8 will need its own migration.
  - **Endpoints:** rename `/lists/<pk>/rename/`, delete `/lists/<pk>/delete/` (GET confirms, POST deletes), add item `/lists/<pk>/items/add/`, remove item `/lists/<pk>/items/<entry_pk>/remove/`, and entry delete `/library/entries/<pk>/delete/`.
  - **Behavior:** a duplicate add is quietly ignored. A list's "Date added" sort uses the date the movie entered your library, not the date it joined the list.
- **Sideways:**
  - Behavior 2's test passed as soon as the view called `.delete()`, because the model's delete settings already did the work. This was said up front; the test guards that choice.
  - Two shell heredocs containing non-ASCII characters (✕, “ ”) failed in Git Bash: one cut a template short and the other didn't run. The template was rewritten with the Write tool and the tests were appended with Edit.
  - The first add-to-list design used inline JavaScript to rewrite the form's URL. It was replaced with a no-JavaScript dropdown of one form per list.
  - The rename form's Cancel first used `hx-get` on the list page into `body`, which would have swapped in only the browse partial. It was caught by reading the template back and made a plain link.
  - A blank list name showed Django's generic "This field is required." The new test caught it, and it was fixed by setting the field's required message.
  - Ruff's formatter split two lines that were too long.
  - The auto-generated migration was renamed before being committed or applied.
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser, so the modals and dropdown weren't checked visually.
  - `CLAUDE.md` was not updated in this session.

## 2026-11-17 — Logged the Phase 6 session and updated CLAUDE.md with Phase 6 conventions

### Prompts
1. `log the session to PROMPTS.md, update CLAUDE.md, then commit and push`

### Summary
- **Outcome:** Added this entry. Updated the "Conventions in use" section of `CLAUDE.md` with what Phase 6 established and tested:
  - the movie-service bullet now covers `refresh_movie` (TMDB is called before anything changes, so a failure leaves the row and `last_fetched_at` untouched) and describes `_store_details` as shared by first save and refresh;
  - a new bullet says the entry page's movie section is `catalog/partials/movie_details.html` (`#movie-details`), swapped whole by Refresh, and that non-HTMX fallbacks redirect with Django messages, which `base.html` now renders.

  The `refresh_movies` command line was already added to the Commands section in the Phase 6 commit. Committed and pushed together with this entry.
- **Deviations:** None. Only conventions already in the code were added.
- **Sideways:** The Phase 6 entry was written before its commit and push, so it doesn't record that Phase 6 was committed as `92409cc` and pushed to `origin/main`; it's noted here instead.

## 2026-11-17 — Implemented Phase 6 (refresh from TMDB: button and command) with TDD

### Prompts
1. `/implement phase 6`
2. `yes` (approved three TDD behaviors: refresh replaces details and genres and moves `last_fetched_at` forward; a failed refresh from the entry page keeps the stored movie and shows an alert; `refresh_movies` refreshes only movies older than the cutoff)
3. `yes pass it` (approved the RED refresh-service test)
4. `yes` (moved on to behavior 2)
5. `yes pass it` (approved the RED failed-refresh test)
6. `yes` (moved on to behavior 3)
7. `yes pass it` (approved the RED command-cutoff test)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **`catalog.services.refresh_movie`:** fetches from TMDB first, then reuses `_store_details` in a transaction. It updates the same row, replaces the genre set and moves `last_fetched_at` forward. A TMDB failure changes nothing.
  - **`POST /find/refresh/<tmdb_id>/` (`catalog:refresh`):** sign-in only, and 404 unless the movie is in the user's library.
    - With HTMX, it returns the movie-details section with an "Updated from TMDB." status, or an error alert that says the stored details are unchanged.
    - Without HTMX, it redirects to the entry page with a Django message. Messages now render in `base.html`.
  - **Entry page:** the movie section moved into `catalog/partials/movie_details.html` (`#movie-details`), with a **Refresh from TMDB** button (spinner, button disabled while the request runs) and "Last updated" date.
  - **`refresh_movies` command:** `--older-than DAYS` (default 180, negative rejected). It refreshes stale movies oldest first, carries on past failures (reported on stderr), and prints a count and a "Done: N refreshed, M failed." summary.
  - **Docs:** the README has a "Refreshing cached TMDB data" section, and the `CLAUDE.md` Commands section lists `refresh_movies`.
  - **Checks:** 125 tests pass (3 TDD plus ordinary tests for successful refresh, the button wiring, the non-HTMX redirect with a message, sign-in, 405, 404 for a movie not in your library, the command carrying on past failures with its summary, nothing stale, and negative days). Ruff is clean, no migrations are missing, and the CSS was rebuilt.
  - **Live check against real TMDB:** the button refreshed a deliberately out-of-date Inception row, the command refreshed a 400-day-old row, and with a bad token the command reported the 401 and left the row and timestamp unchanged. The data was cleaned up. The script stopped early if the database already held movies, so real data couldn't be touched.
- **Deviations:** The user approved all three behaviors and RED tests without changes. The agent's own choices:
  - The refresh URL `/find/refresh/<tmdb_id>/` lives in the catalog app, as the PRD says catalog owns refresh. It's limited to movies in the requester's library.
  - The details section and the alert swap together.
  - Django messages were added to the base layout for the non-HTMX fallback.
  - The command writes per-movie lines and refreshes oldest first.
  - `CLAUDE.md` got only the new command line in this session.
- **Sideways:**
  - Ruff flagged two lines that were too long (the command's summary line and one in the behavior-2 test); its formatter split them, which is a mechanical change.
  - The command prints a movie's title after refreshing, so a renamed movie is logged under its new title.
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser, so the spinner and button disabling weren't checked visually.

## 2026-11-17 — Logged the Phase 5 session and updated CLAUDE.md with Phase 5 conventions

### Prompts
1. `log the session to PROMPTS.md, update CLAUDE.md, then commit and push`

### Summary
- **Outcome:** Added this entry. Updated the "Conventions in use" section of `CLAUDE.md` with what Phase 5 established and tested:
  - the HTMX bullet now notes that history-restore requests get the full page;
  - a new bullet on the shared browse module `library/browse.py`: `clean_params`, the parameter names, `browse_entries`, `browse_context`, passing an already-limited queryset, and rendering through `library/partials/browse.html` in `#library-browse` with `hx-push-url` and `{% querystring %}`;
  - a new bullet with the lessons from ad-hoc checks against the real database: use `shell -c "exec(...)"`, call `setup_test_environment()` before reading `response.context`, set `PYTHONIOENCODING=utf-8`, and clean up in `finally`.

  Committed and pushed together with this entry.
- **Deviations:** None. Only conventions and workflow lessons already seen in this project were added.
- **Sideways:** The Phase 5 entry was written before its commit and push, so it doesn't record that Phase 5 was committed as `8b7a004` and pushed to `origin/main`; it's noted here instead. That entry also said `CLAUDE.md` had not been updated, and this entry fixes that.

## 2026-11-17 — Implemented Phase 5 (library browsing) with TDD

### Prompts
1. `/implement phase 5`
2. `yes` (approved three TDD behaviors: search over title or notes; status/genre/min-rating/decade filters that narrow and combine; rating sort with unrated last both ways)
3. `yes pass it` (approved the RED search test)
4. `yes` (moved on to behavior 2)
5. `make it pass` (approved the RED filters test, including `genre` as a TMDB genre id, "N stars and up", and inclusive decade boundaries)
6. `yes` (moved on to behavior 3)
7. `make it pass` (approved the RED rating-sort test)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **`library/browse.py`:** the shared browse module for the library page now, and for list pages and the API later. It contains:
    - `clean_params`: validates `q`, `status`, `genre` (TMDB id), `min_rating`, `decade`, `sort` and `dir`; invalid values are ignored;
    - `browse_entries`: title or notes search, filters combined with AND, and five sorts (title ignores case) with missing values last in both directions and newest-added first as the tie-break;
    - `filter_options`: only the genres and decades present in the set being browsed;
    - `browse_context`: 20 per page plus the data the template needs.
  - **Shared partial `library/partials/browse.html`:** search box, five filter or sort selects, result count, "Clear filters", the cards, a "no matches" message, an empty-library state (with an optional `empty_message`) and Previous/Next page links built with `{% querystring %}`.
  - **HTMX:** the form and page links swap `#library-browse` with `hx-push-url`, so every setting is in the URL. HTMX requests get the partial; full loads and HTMX history restores get the whole page.
  - **Checks:** 112 tests pass (3 TDD plus ordinary tests for each sort, ignored invalid values, page size and range, page links keeping settings, partial versus full page, history restore, selected controls, library-only options and the empty and no-match states). Ruff is clean, no migrations are missing, and the CSS was rebuilt. A live check on the real database with 25 entries confirmed paging, notes search, rating sorts in both directions and combined filters, and the data was cleaned up.
- **Deviations:** The user approved all three behaviors and RED tests without changes. The agent's own choices:
  - Parameter names (`q`, `status`, `genre`, `min_rating`, `decade`, `sort`, `dir`, `page`) and sort keys (`added`, `title`, `rating`, `released`, `watched`).
  - Default direction: ascending for title, descending for the others.
  - Missing values sort last for the release-date and date-watched sorts too, not just rating.
  - The filter dropdowns list only genres and decades present in your library.
  - The search box, controls and results swap together, so they stay in step with the URL and the back button.
  - Noted but not fixed: SQLite's `icontains` ignores case for ASCII letters only.
- **Sideways:**
  - During the build, sort and direction parsing ended up in two places. `browse.py` was rewritten around a single `clean_params`.
  - The first live check failed because `response.context` is `None` outside the test runner without `setup_test_environment()`. The second failed printing "★" to the Windows console. Both times the `finally` block removed the temporary data, which was confirmed before the third, successful run with UTF-8 output.
  - A CSS spot check first seemed to show `md:grid-cols-6` missing; that was an escaping mistake in the grep pattern, and the class was present.
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser, so URL pushing and back-button behavior weren't checked visually.
  - `CLAUDE.md` was not updated in this session.

## 2026-11-17 — Logged the Phase 4 session and updated CLAUDE.md with Phase 4 conventions

### Prompts
1. `log the session to PROMTS.md and then update CLAUDE.md with any necessary information and then commit and push`

### Summary
- **Outcome:** Added this entry. Updated `CLAUDE.md` with what Phase 4 established and tested:
  - the CSS rebuild note and the template bullet now mention that Tailwind scans `*/forms.py`;
  - form fields use a `data-field` fieldset wrapper with their errors directly below;
  - the entry-rule contract: save through a form or `full_clean()`, never raw `.update()`; `Entry.clean()` rejects or clears based on `_saved_status`; the API serializer must reuse it;
  - other users' objects return 404 through `get_object_or_404(..., user=request.user)`;
  - `static/js/app.js` holds small enhancements, and pages must work without it.

  Committed and pushed together with this entry.
- **Deviations:** None. Only conventions already in the code were added.
- **Sideways:** The Phase 4 entry was written before its commit and push, so it doesn't record that Phase 4 was committed as `1af8f89` and pushed to `origin/main`; it's noted here instead. That entry also said `CLAUDE.md` had not been updated, and this entry fixes that.

## 2026-11-17 — Implemented Phase 4 (entry page and in-place editing) with TDD

### Prompts
1. `/implement phase 4`
2. `go ahead` (approved three TDD behaviors and the proposed design: the model remembers its last-saved status, so changing away from Watched clears the watched-only fields while a never-Watched entry with them filled in is rejected)
3. `yes pass it` (approved the RED per-field model-rule test)
4. `yes` (moved on to behavior 2)
5. `yes pass it` (approved the RED clear-on-leaving-Watched test)
6. `yes` (moved on to behavior 3)
7. `yes pass it` (approved the RED invalid-save test, including a `data-field` wrapper for each form field)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **The rule, defined once:** `Entry.clean()` puts it in one place. Rating, date watched and times watched above 0 are rejected, each against its own field, unless the entry is Watched. If the entry's last-saved status (`_saved_status`, tracked in `__init__`/`save`) was Watched, the three fields are cleared instead.
  - **Forms:** `EntryForm` uses star radios with an "Unrated" choice; watched-only inputs are disabled in the HTML unless Watched, and missing inputs mean empty. `EntryStatusForm` backs the library card's status control.
  - **Pages and endpoints:**
    - Entry page `/library/entries/<pk>/`: poster, details (date, runtime, score, genres, overview) and a panel showing status, stars, date, count and plain-text notes with line breaks kept. HTMX requests get just the panel.
    - `/library/entries/<pk>/edit/`: HTMX Edit, Save and Cancel swaps in `#entry-panel`, with a full-page fallback that redirects after a valid POST.
    - `POST /library/entries/<pk>/status/`: the library card's in-place status control, which returns the updated card.
    - Other users' entries return 404 everywhere.
  - **Library cards:** moved to a partial, now link to the entry page and show stars.
  - **Supporting files:** `static/js/app.js` (enables or disables watched-only inputs and powers the Clear rating button), plus status-badge and star partials.
  - **Tailwind:** now also scans `*/forms.py` for widget classes.
  - **Checks:** 85 tests pass, ruff is clean, no migrations are missing, and the CSS was rebuilt. A live check against the real database exercised detail, edit, save and the card status control (leaving Watched cleared the fields).
- **Deviations:** The user approved the design, all three behaviors and the RED tests without changes. The agent's own choices:
  - Endpoints `/library/entries/<pk>/edit/` and `/status/` (the plan fixed only the entry page URL).
  - A small vanilla-JS file for enabling or disabling the star inputs, which HTMX alone can't do.
  - Read-only stars shown as ★/☆ text with an aria-label.
  - An invalid card status leaves the entry unchanged and shows an inline error.
  - Non-HTMX status changes redirect to the library.
- **Sideways:**
  - Behavior 3's test first checked kept notes as `>Changed notes.<`. Django's textarea puts a newline after the tag, so the check was repaired mechanically to look for `Changed notes.</textarea>` in the notes field.
  - The first CSS build was missing DaisyUI's `textarea` class, because classes set in `forms.py` weren't scanned. Spotted while checking the CSS, and fixed by adding `@source "../../*/forms.py"`. The comment edit left a slightly repetitive comment in `input.css`.
  - Ruff's reformat fixed one line that was too long in a new test.
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser, so the star widget's look and the JS toggling weren't checked visually.
  - `CLAUDE.md` was not updated in this session.

## 2026-11-17 — Logged the Phase 3 session and updated CLAUDE.md with Phase 3 conventions

### Prompts
1. `log the changes to PROMPTS.md and insert any necessary inormation into CLAUDE.md and then commit and push`

### Summary
- **Outcome:** Added this entry. Updated the "Conventions in use" section of `CLAUDE.md` with what Phase 3 established and tested:
  - every Movie lookup by TMDB id goes through `catalog.services.get_or_fetch_movie`, and `_store_details` is there for refresh to reuse;
  - posters are rendered with `partials/poster.html`;
  - duplicates are prevented by database unique constraints, using `transaction.atomic()` plus `IntegrityError` rather than check-then-create;
  - the new `make_movie` fixture and the automatic fast-password-hasher fixture.

  The poster-placeholder note moved from the TMDB client bullet to the new poster bullet. Committed and pushed together with this entry.
- **Deviations:** None. Only conventions already present in the code were added.
- **Sideways:** The Phase 3 entry was written before its commit and push, so it doesn't record that Phase 3 was committed as `7f632c1` and pushed to `origin/main`; it's noted here instead. That entry also said `CLAUDE.md` had not been updated, and this entry fixes that.

## 2026-11-17 — Implemented Phase 3 (save to library and basic library page) with TDD

### Prompts
1. `/implement phase 3`
2. `yes` (approved three TDD behaviors: get-or-fetch stores an unstored movie with genres; saving a stored movie works while TMDB is down; saving twice keeps one entry and shows "In library ✓")
3. `pass it` (approved the RED get-or-fetch test)
4. `yes` (moved on to behavior 2)
5. `yes make it pass` (approved the RED save-while-TMDB-down test)
6. `yes` (moved on to behavior 3)
7. `yes pass it` (approved the RED duplicate-save test, including the rule that a second save leaves the existing status unchanged)
8. `yes` (approved building the rest of the phase normally)

### Summary
- **Outcome:**
  - **Models:** `Genre` and `Movie` in catalog (TMDB id unique; poster path stored, URL built at render). `Entry` in library (status choices, 1–5 rating validators, notes, date watched, times watched, timestamps, unique user + movie). Migrations were added and applied locally.
  - **Get-or-fetch service (`catalog/services.py`):** `get_or_fetch_movie` returns the stored movie without calling TMDB. Otherwise it calls the new `tmdb.get_movie_details` and stores every field, genres (shared, never duplicated) and `last_fetched_at` in one transaction. If two saves race, the second one returns the stored row. If TMDB fails for an unstored movie, it raises `TMDBError`.
  - **Save action:** `POST /find/save/<tmdb_id>/` (`catalog:save`), sign-in required.
    - The status field accepts only "Want to watch" or "Watched"; anything else becomes "Want to watch".
    - Duplicates are blocked by the database constraint, and a second save leaves the existing entry unchanged.
    - An unstored movie with TMDB down shows an alert and keeps the Save control.
    - A non-HTMX request redirects to the library.
  - **Search results:** each card has a Save dropdown, or "In library ✓" when the user already has the movie.
  - **Library page:** shows only the user's entries, newest first, as cards with poster, title, year and a status badge. It works from local data only.
  - **Shared poster partial:** `templates/partials/poster.html`, with the placeholder used both when there's no poster and when the image fails to load.
  - **Admin:** registered the new models.
  - **Tests:** the three TDD tests plus ordinary tests, 56 in total, all passing. Ruff is clean, no migrations are missing, and the CSS was rebuilt.
  - **Live check against real TMDB:** saved Inception with real details and genres; search showed "In library ✓"; with a bad token, re-saving a stored movie worked, an unstored save showed an alert, and the library rendered. Temporary data was cleaned up.
- **Deviations:** The user approved all three behaviors and RED tests without changes. The agent's own choices:
  - The save URL `/find/save/<tmdb_id>/` was picked because the plan didn't fix one.
  - Unknown statuses fall back to "Want to watch" rather than returning an error.
  - Non-HTMX saves redirect to the library.
  - `Entry.movie` uses PROTECT, so a movie can't be deleted while entries use it (the PRD keeps unused movies anyway).
  - `poster_path` keeps `null=True` as the PRD says, with a commented `noqa: DJ001`.
  - An automatic fast-password-hasher fixture cut the suite from about 100 seconds to about 4.
- **Sideways:**
  - Behavior 2 used `Entry.objects.create` on purpose, so behavior 3 started as a real 500 error from the unique constraint.
  - One ordinary test was badly written: it created the same entry in a tangled way. It was rewritten before running.
  - The library poster test first counted `onerror=` (which appears twice per image because of `this.onerror=null`) and was fixed to count the attribute.
  - The pages were checked with HTTP requests and Django's test client only; nobody viewed them in a browser.
  - `CLAUDE.md` was not updated in this session.

## 2026-11-16 — Logged the Phase 2 session and updated CLAUDE.md with Phase 2 conventions

### Prompts
1. `Log the session in PROMPTS.md and update CLAUDE.md with any necessary information`

### Summary
- **Outcome:** Added this entry. Updated the "Conventions in use" section of `CLAUDE.md` with what Phase 2 established and tested:
  - the `catalog:` URL namespace;
  - the HTMX pattern: a full page that includes a partial, and views that return only the partial for `request.htmx`;
  - the TMDB client contract: `catalog/tmdb.py`, `TMDBError` with `kind` and `message`, views calling it as `tmdb.<function>`, and errors shown as a `role="alert"` with HTTP 200;
  - the poster URL helper and placeholder image;
  - the automatic test fixture that sets a dummy token, blocks real HTTP, and the pattern for faking TMDB in tests.

  The other sections are unchanged.
- **Deviations:** None. Only conventions that already exist in the code were added.
- **Sideways:** The Phase 2 entry was written before the commit and push, so it doesn't record that Phase 2 was committed as `178f296` and pushed to `origin/main`; it's noted here instead. That entry also said `CLAUDE.md` had not been updated with the test fixture, and this entry fixes that. This entry and the `CLAUDE.md` changes are not committed yet.

## 2026-11-16 — Implemented Phase 2 (Find movies, search only) with TDD

### Prompts
1. `/implement phase 2 of the plan`
2. `yes` (approved three TDD behaviors: client error mapping; HTMX search returns the results partial; TMDB failure shows an alert in the results area)
3. `yes pass as written` (approved the RED client error-mapping test)
4. `yes` (moved on to behavior 2)
5. `pass it` (approved the RED HTMX results-partial test)
6. `yes` (moved on to behavior 3)
7. `make it pass` (approved the RED failure-alert test)
8. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:** Built `/find/` (`catalog:find`, sign-in required).
  - **TMDB client (`catalog/tmdb.py`):** the only module that calls TMDB. It uses a 10-second timeout and raises one `TMDBError` with a `kind` and a user-readable `message`. The kinds are timeout, connection, request, 401 auth, 429 rate limit, other HTTP errors (with TMDB's `status_message`), invalid JSON, and a missing token (`not_configured`). It also has a `poster_url` helper.
  - **Search page:** searching happens on submit through HTMX (`hx-get` into `#results`, with the query pushed to the URL). A non-HTMX request gets the full page with the same results partial.
  - **Results:** each card shows the poster, title, year and an overview cut to 150 characters. Missing posters and posters that fail to load fall back to `static/img/poster-placeholder.svg`. A search with no results shows a "No movies found… try different words" message. Any `TMDBError` appears as a DaisyUI error alert inside the results area with a 200 status.
  - **Navbar:** now has a "Find movies" link.
  - **Tests:** the three TDD behaviors, plus ordinary tests for the extra error kinds, the token, query and timeout sent to TMDB, poster URLs, sign-in, empty and blank queries, the full-page response, no results, the placeholder, HTML escaping and the unconfigured-token alert. A new automatic fixture in the root `conftest.py` sets a dummy token and makes any real `requests.get` fail the test.
  - **Results of checks:** 38 tests pass, ruff is clean, and the CSS was rebuilt. A live check against the real TMDB API confirmed real results (HTMX and full page), the no-results message, and the bad-token (401) alert.
- **Deviations:** The user approved all three behaviors and RED tests without changes. The agent's own choices:
  - Error messages were reworded from the console script for website visitors. For example, the 401 message says the site's configuration needs fixing instead of telling the reader to edit `.env`.
  - A `not_configured` error was added for a missing token, and a `request` kind for other `requests` errors. Neither was in the plan.
  - TMDB failures return 200 so HTMX swaps the alert in.
- **Sideways:**
  - Behavior 3's first run raised the view's exception instead of failing on an assertion. The test was changed to set `raise_request_exception = False` so it sees the 500 a browser would get; it still checks the same thing.
  - Ruff flagged two lines that were too long, one of them in an approved test; both were split mechanically.
  - The first live check piped a script into `manage.py shell`, which ran it as interactive input and left a throwaway `zz_live_check` user behind. That user was deleted, the check was re-run with `shell -c`, and the second run cleaned up after itself.
  - The pages were checked with HTTP requests only; nobody viewed them in a browser.
  - `CLAUDE.md` was not updated with the new test fixture.

## 2026-11-16 — Logged the Phase 1 session and updated CLAUDE.md with verified commands and conventions

### Prompts
1. `log the session to PROMPTS.md with the standard prompt and update CLAUDE.md with any necessary information`

### Summary
- **Outcome:** Added this entry. Updated `CLAUDE.md` with two new sections, now that the tooling is installed and verified:
  - **Commands (verified):** run/migrate, pytest, ruff, and the Tailwind CSS build.
  - **Conventions in use:** project-level `templates/`; namespaced app URLs with `@login_required`; HTMX pinned at 2.0.11 with the CSRF token sent through `hx-headers`; tests in per-app `tests/` packages with shared fixtures in the root `conftest.py`.
  - The original stack, architecture and reference sections are unchanged.
- **Deviations:** None. The new sections hold only commands and conventions that Phase 1 already uses and tested. They add nothing new about later phases.
- **Sideways:** The previous entry, which covers the Phase 1 prompts, was written before the commit and push. It doesn't record that Phase 1 was committed as `389cacc` and pushed to `origin/main`, so it's noted here; that entry was left unchanged, following the log rules. This entry and the `CLAUDE.md` changes are not committed yet.

## 2026-11-16 — Wrote CLAUDE.md and implemented Phase 1 (skeleton and accounts) with TDD

### Prompts
1. `Create the initial CLAUDE.md for this project. Keep it to about 20-30 lines. Include only: 1. A one-line project description. 2. The approved technology stack and package manager. 3. Durable, project-wide architecture decisions already established in the PRD. 4. Short pointers to the PRD, plan, and prototypes instead of repeating their details. Do not add commands yet because the project tooling has not been installed or verified. Do not predict project structure, paths, template conventions, URL conventions, or testing commands that do not exist yet. Do not copy business requirements, user stories, implementation phases, rejected alternatives, or detailed feature rules into CLAUDE.md. Do not invent new architectural conventions.`
2. `/implement phase 1 of the plan`
3. `yes, go ahead with those two` (approved the two TDD behaviors: sign-up signs in and lands on the library; signed-out library request redirects to login with `next`)
4. `yes make it pass as written` (approved the RED sign-up test)
5. `yes` (moved on to the second behavior)
6. `make it pass` (approved the RED redirect test)
7. `go ahead` (approved building the rest of the phase normally)

### Summary
- **Outcome:** Wrote a 25-line `CLAUDE.md`: description, stack, the architecture decisions from the PRD, and pointers to the PRD, plan and prototype. It has no commands, paths or URL conventions. Then built Phase 1:
  - The `config` project and `accounts`/`catalog`/`library` apps. Secrets (`DJANGO_SECRET_KEY`, `TMDB_READ_ACCESS_TOKEN`) are read from the environment through `uv run --env-file .env`.
  - Packages: django-htmx, plus ruff, pytest and pytest-django as dev dependencies.
  - Styling: Tailwind v4.3.5 standalone CLI (binary git-ignored in `tools/`), DaisyUI 5.8.1 plugin files in `assets/tailwind/`, and the built `static/css/app.css` committed. HTMX 2.0.11 is served locally.
  - Pages: a base layout with navbar and TMDB attribution footer, sign-up, login and logout (POST), `/` redirecting to `/library/`, and a sign-in-only empty library page.
  - TDD covered two behaviors. Sign-up creates the account, signs the user in and lands on the library. A signed-out `/library/` request redirects to login with `next`. Twelve more ordinary tests cover sign-up and login errors, login with `next`, logout, home redirect, attribution and the local CSS/HTMX files.
  - Final result: 14 tests pass, `ruff check` and `ruff format --check` are clean, `manage.py check` reports no issues, and the real dev server serves every page and static file. README now documents setup, tests, linting and the Tailwind build.
- **Deviations:** The user approved both TDD behaviors and both RED tests without changes. The agent made several choices that were not discussed:
  - HTMX 2.0.11 instead of the newer 4.0.1, so it works with django-htmx.
  - A development-only fallback secret key, so tests run without `.env`.
  - The site follows the system's light or dark theme instead of always being dark like the prototype.
  - A real `DJANGO_SECRET_KEY` was generated and added to the local `.env`.
  - `ruff format` also reformatted `scripts/tmdb_search.py`, which changed only its layout.
- **Sideways:** The first version of the redirect test compared the exact `Location` text with `next` encoded as `%2Flibrary%2F`. Django leaves the slashes unencoded, so the test failed even after the fix. It was repaired mechanically to compare the parsed path and `next` value; the behavior checked did not change. Ruff flagged unused imports in the empty generated `admin.py`/`models.py`/`views.py` stubs, and `--fix` removed them. The dev server started for the check was stopped afterwards. The pages were checked with HTTP requests only; no one viewed them in a browser. `.claude/settings.local.json` stays uncommitted as personal settings.

## 2026-11-16 — Broke the movie watch-log PRD into a 10-phase tracer-bullet plan

### Prompts
1. `/prd-to-plan`
2. `i approve the plan, write it`
3. `log the session to PROMPTS.md with the standard format`

### Summary
- **Outcome:** Read `prd/movie-watch-log.md` and checked the repo. It had no Django code yet, only `scripts/tmdb_search.py`, the rating prototype and the uncommitted Django/DRF dependencies. Proposed the URL layout and the model and app ownership, plus 10 vertical-slice phases: skeleton and accounts, Find movies search, save to library with a basic library page, entry page and in-place editing, library browsing, refresh from TMDB, named lists, visibility and sharing on the website, API token and entries API, and lists API. Each phase is mapped to PRD user stories. After approval, wrote `plans/movie-watch-log.md` with the architectural decisions in the header and acceptance criteria for each phase. No application code was written.
- **Deviations:** Approved the proposed breakdown as-is. The agent offered three optional changes (merge the two API phases, fold refresh into the entry-editing phase, split Phase 1 into tooling and accounts), and none were taken. The agent chose the URL paths (`/find/`, `/library/`, `/lists/`, `/u/<username>/`, `/shared/`, `/api/...`) because the PRD did not fix them, and the user accepted them without changes. The agent moved story 24 (entry delete with a list-count warning) to the named-lists phase so the count has lists to refer to.
- **Sideways:** Nothing failed. The PRD was not in context after `/clear`, so the agent found and read it from `prd/` rather than asking. Nothing was committed, and the earlier uncommitted changes remain.

## 2026-11-16 — Designed the movie watch-log app with grill-me, prototyped the rating look, wrote the PRD

### Prompts
1. `/grill-me create an application thats purpose is to allows users to create lists of their watched movies. These are the requirements: Use the TMDB API. Users can save selected items to your application - Store enough information locally for saved items to remain accessible when the external API is unavailable. Users can add and edit their own information - this includes notes, ratings,and  status/progress. Users can browse their saved items on a website - Include search, filtering, sorting, and pagination. These features must operate on locally saved data. Users must sign in to manage their saved data - they may choose private data, public viewing, or selective sharing and enforce those rules through both the website and the API. Your application provides its own API - Support listing, creating, updating, and deleting saved entries. The application handles unsuccessful external requests - Show a useful message when the provider is unavailable or a request fails. The project must use: Django , Django REST Framework (DRF) , SQLite , uv , Ruff , Styling must use Tailwind with DaisyUI , Interactivity must use HTMX , and Testing must use Django's built-in testing framework or pytest.`
   - Grill-me answers, in order: Library + named lists (B); Visibility per list only (A); Share by username (A); Public lists readable by logged-out visitors (A); Status + date watched + times watched (B).
2. `/prototype` (no arguments, given while the rating-scale question was open)
   - Answered the "which decision?" dialog with: "the stars look on the most recent question"
3. `Do A`
4. Grill-me answers continued, one per prompt: Rich local TMDB copy, posters hotlinked (B); Shared `Movie` + per-user `Entry` (A); One-click Save with status dropdown (A); Search title/notes, filter status/genre/min rating/decade, five sorts, 20 per page (B); Session + DRF token auth (B); API create by `tmdb_id`, 503 when TMDB is down (A); Manual refresh button + `refresh_movies` command (B); Tailwind standalone CLI + DaisyUI plugin, built CSS committed (B); pytest + pytest-django (B); Profile pages + "Shared with me" (B); Entry delete cascades to lists with a counted warning (A); `config` + `accounts`/`catalog`/`library` apps (B); HTMX in-place editing (B).
5. `/to-prd`
6. `log the session to PROMPTS.md with the standard format`

### Summary
- **Outcome:** Settled 19 design questions for a Django + DRF movie watch-log app. Built a throwaway Tailwind/DaisyUI prototype, `prototypes/rating-scale.html`, comparing 1–5 stars, half stars and a 1–10 score. Whole stars (A) were chosen, and the decision is recorded in the file's header comment. Wrote the PRD to `prd/movie-watch-log.md`, with 62 user stories, implementation decisions, out-of-scope items and further notes. No application code was written.
- **Deviations:** Question 1: chose library + named lists (B) instead of the recommended single library (A). Question 5: did not say whether to add a "Dropped" status, so it was left out. Question 6: did not answer whether rating should be allowed only once a movie is Watched; the rule was kept as recommended and shown in the prototype. Question 9: "A" was read as one-click Save *with* the status dropdown. The PRD added TMDB attribution on the site, which was not discussed, because TMDB's terms require it. Every other answer took the recommended option.
- **Sideways:** `/prototype` was run without arguments, so the agent asked which decision it should answer before building. The prototype was opened in the browser but the agent did not visually check it. It loads DaisyUI 5.0.43 and `@tailwindcss/browser` 4.1.11 from jsDelivr, and those version numbers were not verified. The Django/DRF additions in `pyproject.toml`/`uv.lock` and `.claude/settings.local.json` remain uncommitted, and nothing was committed this session.

## 2026-11-15 — Researched free APIs, chose TMDB, built and verified a uv console search script

### Prompts
1. `/research Find free external APIs for a Django application where users search for items, save them, and add their own notes, ratings, or progress. Explore topics such as recipes, books, movies, television, games, music, and more. Compare promising providers using official documentation, including available data, free limits, signup requirements, etc...`
2. `/grill-me write a short console script that makes a real request to the TMDB API. The script must: Accept user input, such as a search phrase or item identifier. Make a meaningful request to the external API. Use your own credentials if the provider requires them. Display selected results clearly in the console. Handle unsuccessful requests and empty results with useful messages. This script belongs to a future Django project that will use uv so setup the script with uv instead of a different package manager.`
   - Grill-me answers, in order: Movies only; Read Access Token; `uv run --env-file`; requests; Root project with `scripts/`; Argument or prompt; Top 5 with overview; Specific errors + exit codes; Manual check only.
3. `yes` (approved building the agreed plan)
4. `I added the token to .env, run the real search`
5. `update PROMTPS.md in the standard format, commit with the message: Research API provider and verify external API access. and push`

### Summary
- **Outcome:** A background agent wrote `research/free-apis-for-search-save-annotate-app.md`, comparing about 25 free APIs against their official docs. Top picks: TVmaze, Open Library, TMDB, TheMealDB, Jikan. Set up a uv project (`uv init --bare`, `uv add requests`) and wrote `scripts/tmdb_search.py`, which searches TMDB movies by command-line argument or prompt and prints the top 5 with year, rating, TMDB ID and a short overview. Added `.env.example`; the real token lives in the git-ignored `.env`. Verified against the live API: real search, multi-word prompt search, zero results, blank input, missing token and bad token (401) all print useful messages.
- **Deviations:** Chose loading the token with `uv run --env-file .env` instead of the recommended `.env` + python-dotenv, so the run command must include the flag. All other grill-me answers took the recommended option.
- **Sideways:** Eight providers' official docs blocked automated fetching (IGDB, AniList, BoardGameGeek, Hardcover, Discogs, Open Brewery DB, Art Institute of Chicago, Podcast Index). The research cites search-engine snippets of those pages and labels them "(via search index)"; MyAnimeList and Kitsu are marked unverified. Research also found Spotify, Spoonacular, Listen Notes, Edamam, Marvel and Punk API unsuitable or gone. The shell had another project's virtualenv active (`django-test`), causing a harmless uv `VIRTUAL_ENV` mismatch warning. Real-search testing waited until the user added their own token. `.claude/settings.local.json` was left uncommitted as personal settings.
