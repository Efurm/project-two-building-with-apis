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
