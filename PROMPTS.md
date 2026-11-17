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
