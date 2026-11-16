# Free external APIs for a "search → save → annotate/track progress" Django app

**Checked:** 2026-11-15. **Method:** Claims were checked against provider-owned pages: official docs, terms, pricing pages, developer portals and provider-run forums or wikis. Several official pages block automated fetching (HTTP 403): IGDB, AniList (docs.anilist.co), BoardGameGeek, Hardcover, Discogs, Open Brewery DB, Art Institute of Chicago and Podcast Index. For those, the facts come from the provider's own pages as indexed by search, or from the provider's official mirror (AniList's GitBook). Each such case is marked *(official page, via search index)*. Anything I could not confirm is marked **not documented** or **unverified**.

---

## 1. Summary / recommendation

### Top picks

| # | API | Domain | Why it fits |
|---|-----|--------|-------------|
| 1 | **TVmaze** | TV | No key needed. CC BY-SA licence allows storing data with attribution. Has episode lists with season/number, so "watched S2E4" fits naturally. Image URLs never change, so they can be cached indefinitely. |
| 2 | **Open Library** | Books | No key needed. Free-text search, stable work/edition keys, cover image URLs and page counts. Reading progress ("120/300 pages") is the obvious use. The only rule is 1–3 requests per second plus a User-Agent header. |
| 3 | **TMDB** | Movies (and TV) | Free API key, best-in-class posters and metadata, and up to about 40 requests per second. You need visible attribution, and cached data must be refreshed at least every 6 months. Non-commercial only on the free key. |
| 4 | **TheMealDB** | Recipes | Test key `"1"` is explicitly allowed for development and education. Search by name, filters, stable `idMeal` IDs and images. "Cooked it, 4/5" plus step-based progress. |
| 5 | **Jikan** (or AniList) | Anime/manga | No key needed for Jikan. 60 requests per minute. Returns MyAnimeList IDs, episode and chapter counts, and images. AniList is the GraphQL alternative, but it is currently in a "degraded" state capped at 30 requests per minute. |

Honourable mentions: **RAWG** for video games (20,000 requests per month, backlink required), **MusicBrainz** for music (no key, CC0 core data, 1 request per second), **The Met Collection API** for art (no key, CC0 open-access images), and **Open Brewery DB** for beer (no key).

### Avoid for this project, and why

- **Spotify Web API:** Since February 2026, Development Mode requires the app owner to have **Spotify Premium**, allows **5 users**, and caps search `limit` at **10**. Individuals can no longer apply for Extended Quota (organizations with 250k+ MAU only) ([quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes); [Feb 2026 changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026)).
- **Spoonacular:** The free tier is now **50 points per day** at 1 request per second. Cached data may be kept **only 1 hour**, which conflicts with saving recipes to your database ([pricing](https://spoonacular.com/food-api/pricing)).
- **Listen Notes:** The free tier gives 150 requests per month, and server-side storage of content is prohibited apart from IDs and dates ([pricing](https://www.listennotes.com/api/pricing/)).
- **Edamam Recipe Search:** The current product starts at $9/month. The old free tier appears only on a page marked "Version Retired" ([product page](https://developer.edamam.com/edamam-recipe-api); [retired page](https://developer.edamam.com/recipe-api)).
- **Marvel Comics API:** `developer.marvel.com` now 301-redirects to `www.marvel.com`, so the developer portal appears to be gone.
- **Punk API (beers):** `punkapi.com` does not resolve (DNS ENOTFOUND on 2026-11-15).
- **OMDb:** Usable, but posters (the Poster API) are **patrons-only** and the content is CC BY-NC ([omdbapi.com](https://www.omdbapi.com/)). TMDB is a better choice.
- **BoardGameGeek XML API:** Viable, but since late 2025 it requires **manual application approval** plus a bearer token. Approval reportedly takes "a few days" (see §3.6). Plan around that lead time if you choose board games.

### Surprising findings

- Spotify's February 2026 lockdown, summarized above. Its July 2026 update raised the cap to 25 Client IDs per account but did not remove the Premium requirement or the 5-user cap ([July 2026 blog](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates)).
- Spoonacular's free tier has dropped to 50 points per day. Many tutorials still say 150.
- AniList's own docs open with a degraded-state banner: 30 requests per minute instead of 90.
- The Met's `/v1/search` endpoint was retired on **October 1, 2026**. Use `/v1.1/search`, which adds `offset` and `limit` ([Met API](https://metmuseum.github.io/)).
- Trakt's current docs list **500** GET calls per 5 minutes. Older docs said 1,000.
- BGG now requires registration and tokens for nearly all XML API use.

---

## 2. Comparison table

"Storage OK?" means whether you may keep the item's data (title, image URL and so on) in your own database. Storing just the external ID is fine everywhere.

| API | Domain | Auth | Free limits | Search? | Images? | Storage OK? | Progress unit | Docs |
|-----|--------|------|-------------|---------|---------|-------------|---------------|------|
| TVmaze | TV | None | ≥20 req / 10 s per IP | Yes (fuzzy + single) | Yes (medium/original) | Yes, CC BY-SA with attribution | Episodes (season/number) | [tvmaze.com/api](https://www.tvmaze.com/api) |
| Open Library | Books | None (User-Agent recommended) | 1 req/s (3 req/s with identified User-Agent) | Yes (`search.json`, paging) | Yes (Covers API) | Yes; caching encouraged; no new copyright asserted | Pages | [openlibrary.org/developers/api](https://openlibrary.org/developers/api) |
| Google Books | Books | API key | Not documented on the docs page (set per Cloud project) | Yes (`q`, max 40/page) | Yes (`imageLinks`) | Not documented in Books terms | Pages (`pageCount`) | [developers.google.com/books](https://developers.google.com/books/docs/v1/using) |
| Hardcover | Books | Bearer token (1 year, reset each Jan 1) | 60/min, 5,000/day | Yes (GraphQL) | Yes | Unverified | Pages | [docs.hardcover.app](https://docs.hardcover.app/api/getting-started/) |
| TMDB | Movies/TV | API key or Read Access Token | About 40 req/s | Yes (movie/tv/person) | Yes (posters, backdrops) | Yes, max 6 months then refresh | Runtime / episodes | [developer.themoviedb.org](https://developer.themoviedb.org/docs/getting-started) |
| OMDb | Movies/TV | API key | 1,000/day | Yes (`s`, pages 1–100) | Posters patrons-only | CC BY-NC (not stated otherwise) | Episodes/seasons | [omdbapi.com](https://www.omdbapi.com/) |
| Trakt | Movies/TV | Client ID header (OAuth for user data) | 500 GET / 5 min | Yes | Not verified | Unverified | Episodes | [developer.trakt.tv](https://developer.trakt.tv/docs/rate-limiting) |
| TheMealDB | Recipes | Test key `1` | Not documented | Yes (name, first letter, filters) | Yes (meal + ingredient) | Not documented | Steps / "cooked" + rating | [themealdb.com/api.php](https://www.themealdb.com/api.php) |
| Spoonacular | Recipes | API key | 50 points/day, 1 req/s | Yes | Yes | **1-hour cache only** | Steps | [pricing](https://spoonacular.com/food-api/pricing) |
| RAWG | Video games | API key | 20,000/month | Yes | Yes | Not documented; no redistribution | Hours / % complete | [rawg.io/apidocs](https://rawg.io/apidocs) |
| IGDB | Video games | Twitch client-credentials OAuth | 4 req/s, 8 open requests | Yes (`search`, Apicalypse) | Yes (cover `image_id`) | Yes (per IGDB FAQ) | Hours / % complete | [api-docs.igdb.com](https://api-docs.igdb.com/) |
| BGG XML API2 | Board games | Registered app + bearer token (manual approval) | Not documented | Yes | Yes | Not documented; non-commercial only | Plays / sessions | [using the XML API](https://boardgamegeek.com/using_the_xml_api) |
| MusicBrainz | Music | None (User-Agent required) | 1 req/s | Yes (Lucene, limit/offset) | Via Cover Art Archive | Yes (core data CC0) | Tracks | [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) |
| Discogs | Music | None, or key/secret or token | 25/min unauth, 60/min auth | Yes | Yes | Not verified | Tracks | [discogs.com/developers](https://www.discogs.com/developers) |
| Podcast Index | Podcasts | Key + secret (SHA-1 auth header) | Not documented | Yes (`search/byterm`) | Yes | Free for any lawful purpose incl. commercial | Episodes | [api.podcastindex.org](https://api.podcastindex.org/developer_docs) |
| iTunes Search | Podcasts/books/music | None | About 20 calls/min | Yes (`media=podcast`, etc.) | Yes (60/100 px) | Caching recommended; promo-use terms | Episodes / tracks | [Apple Search API](https://performance-partners.apple.com/search-api) |
| Jikan | Anime/manga | None | 60/min, 3/s | Yes | Yes | Not documented (data scraped from MAL) | Episodes / chapters | [docs.api.jikan.moe](https://docs.api.jikan.moe/) |
| AniList | Anime/manga | None for public queries | **30/min (degraded)**, normally 90/min | Yes (GraphQL) | Yes | Not as a backup/data store; educational projects relaxed | Episodes / chapters | [AniList docs](https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting) |
| MangaDex | Manga | None for reads | About 5 req/s per IP | Yes | Yes | Credit required; no ads or paid services | Chapters | [api.mangadex.org/docs](https://api.mangadex.org/docs/2-limitations/) |
| The Met | Art | None | 80 req/s | Yes (`/v1.1/search`) | Yes (public-domain JPEGs) | Yes (CC0 open access) | Visited / favourite | [metmuseum.github.io](https://metmuseum.github.io/) |
| Art Institute of Chicago | Art | None | 60/min anonymous | Yes | Yes (IIIF) | Yes (CC0, except descriptions are CC BY) | Visited / favourite | [api.artic.edu/docs](https://api.artic.edu/docs/) |
| Harvard Art Museums | Art | API key | 2,500/day (requested) | Yes | Yes (IIIF) | **Max 2 weeks** | Visited / favourite | [GitHub docs](https://github.com/harvardartmuseums/api-docs) |
| NPS | National parks | API key | 1,000/hour | Partial (`/parks` + filters) | Not stated on guide page | Not documented | Visited / hikes done | [NPS guides](https://www.nps.gov/subjects/developer/guides.htm) |
| Open Brewery DB | Breweries | None | None stated | Yes (`/breweries/search`) | No | Not documented | Visited / beers tried | [openbrewerydb.org](https://www.openbrewerydb.org/documentation) |
| Comic Vine | Comics | API key | 200 req per resource per hour | Unverified (see resource list) | Yes | No competing product or redistribution | Issues | [comicvine API](https://comicvine.gamespot.com/api/) |

---

## 3. Per-domain detail

### 3.1 Television

#### TVmaze (recommended)
- **Auth:** The public API documents no key or login step. User-level API access is separate and Premium-only ([TVmaze API](https://www.tvmaze.com/api)).
- **Limits:** At least 20 calls every 10 seconds per IP. Exceeding it returns HTTP 429, so back off and retry. Idle open connections can get an IP blocked ([TVmaze API](https://www.tvmaze.com/api)).
- **Search:** `/search/shows?q=` returns fuzzy, ranked results with full show objects. `/singlesearch/shows?q=` returns a single show or nothing. Shows can also be looked up by TheTVDB or IMDb ID ([TVmaze API](https://www.tvmaze.com/api)).
- **Data and IDs:** Numeric TVmaze IDs. Episodes are available, and the show index pages by ID at 250 per page ([TVmaze API](https://www.tvmaze.com/api)).
- **Images:** An `image` object with `medium` and `original` sizes, or null. Image URLs never change content, so they can be cached indefinitely ([TVmaze API](https://www.tvmaze.com/api)).
- **Licence:** CC BY-SA 4.0, usable "for any purpose". Credit TVmaze; linking back via the API's URLs satisfies attribution ([TVmaze API](https://www.tvmaze.com/api)).
- **Caching:** Most API output is server-cached for 60 minutes ([TVmaze API](https://www.tvmaze.com/api)).
- **Python client:** None official (not documented).
- **Progress fit:** Excellent. Track the last watched episode (season and number) against the episode list.

#### TMDB (also covers TV): see §3.2.

#### Trakt
- Unauthenticated and authenticated GET are each **500 calls per 5 minutes**, and POST/PUT/DELETE are 1 per second, per the current docs (older docs and announcements said 1,000) ([Trakt rate limits](https://developer.trakt.tv/docs/rate-limiting)) *(official page, via search index)*.
- You need an app (client ID) sent in the `trakt-api-key` header ([Trakt create an app](https://developer.trakt.tv/docs/create-an-app)) *(via search index)*.
- Images: not verified. Trakt is mainly a tracking layer that cross-references TMDB/IMDb/TVDB IDs, which duplicates what your app would do, so it is lower priority.

### 3.2 Movies

#### TMDB (recommended)
- **Signup:** Request a key from your account settings' API section after agreeing to the terms. Approval time and credit card: **not documented** ([Getting started](https://developer.themoviedb.org/docs/getting-started)).
- **Auth:** A v3 `api_key` query parameter, or the API Read Access Token as a Bearer header. Neither grants more access than the other ([Application auth](https://developer.themoviedb.org/docs/authentication-application)) *(via search index)*.
- **Search:** Search exists for movies, TV and people, returning a `results` array ([Search & query](https://developer.themoviedb.org/docs/search-and-query-for-details)) *(via search index)*. Responses are JSON only.
- **Limits:** The old 40 requests per 10 seconds limit was disabled in December 2019. The upper limits now sit "somewhere in the 40 requests per second range". Honour HTTP 429 ([Rate limiting](https://developer.themoviedb.org/docs/rate-limiting)).
- **Terms:**
  - Use an approved TMDB logo, less prominent than your own.
  - Show the "not endorsed or certified by TMDB" notice.
  - **Do not cache for more than 6 months.**
  - Commercial use needs a separate agreement.
  - No AI/ML training.
  - No use as an image host.

  Source: [API Terms](https://www.themoviedb.org/api-terms-of-use) (last updated 2023-10-20). The FAQ says the API is free for non-commercial use with attribution ([FAQ](https://developer.themoviedb.org/docs/faq)) *(via search index)*.
- **Django implication:** Store the `tmdb_id` permanently. Treat title, poster path and similar fields as a cache, with an `updated_at` field and a refresh at least every 6 months.
- **Progress fit:** Runtime for movies, episodes for TV.

#### OMDb
- The free key allows 1,000 requests per day. Patreon tiers exist, but prices are not listed ([API key page](https://www.omdbapi.com/apikey.aspx)).
- Search with `s` (pages 1–100), or look up by `i` (IMDb ID) or `t` (title) ([omdbapi.com](https://www.omdbapi.com/)).
- **The Poster API is only available to patrons.** Content is CC BY-NC 4.0 ([omdbapi.com](https://www.omdbapi.com/)).

### 3.3 Books

#### Open Library (recommended)
- **Auth:** None. Apps that make frequent calls should send `User-Agent: AppName (contact email)` ([Open Library APIs](https://openlibrary.org/developers/api)).
- **Limits:** 1 request per second unidentified, 3 per second with an identifying User-Agent. Don't bulk-download (use the data dumps instead), don't send hundreds of single-book calls (use `search.json`), and don't use it as the backend for a high-traffic commercial service. Caching is encouraged ([Open Library APIs](https://openlibrary.org/developers/api)).
- **Search:** `https://openlibrary.org/search.json` with `q`, `fields`, `sort`, `page`/`limit` or `offset`, and `lang`. Docs include `key`, `title`, `author_name`, `cover_i`, `first_publish_year` and `edition_count`. The schema "is not guaranteed to be stable" ([Search API](https://openlibrary.org/dev/docs/api/search)). The search docs don't list a page-count field. Get it from the edition record instead ([Open Library APIs](https://openlibrary.org/developers/api) lists the Work & Edition APIs).
- **Covers:** `https://covers.openlibrary.org/b/{id|isbn|olid}/{value}-{S|M|L}.jpg`.
  - Lookups by anything other than cover ID or OLID are limited to 100 per IP per 5 minutes.
  - Hotlinking to covers.openlibrary.org is requested.
  - A courtesy link back is appreciated.
  - Don't crawl the API.

  Source: [Covers API](https://openlibrary.org/dev/docs/api/covers).
- **Licence:** The Internet Archive "does not assert any new copyright" over the database ([Licensing](https://openlibrary.org/developers/licensing)). No explicit CC0 statement on that page.
- **Progress fit:** Pages.

#### Google Books
- Search needs no OAuth, but you must identify the app with an API key. `maxResults` defaults to 10 and maxes at 40, with `startIndex` paging. Volume IDs look like `_LettPDhwR0C`. `volumeInfo.pageCount` and `imageLinks` are available ([Using the API](https://developers.google.com/books/docs/v1/using)).
- The default daily quota is **not documented** on the docs page. It is managed per Google Cloud project.
- The Books terms bar charging users without permission and require removing content on request. They don't cover caching. The page was last modified in 2012 and defers to the Google APIs ToS ([Books terms](https://developers.google.com/books/terms)).
- Bonus: Google's own bookshelves ("Reading Now", "Have Read") exist but require OAuth, which isn't needed here.

#### Hardcover
- GraphQL API. Free plan: 60 requests per minute (burst of 10) and 5,000 per day. Each top-level field counts as one request ([Getting started](https://docs.hardcover.app/api/getting-started/)) *(via search index)*.
- Tokens are valid for one year and reset every January 1. Calls must be made server-side only. The API is in beta and may break or reset tokens without notice ([Getting started](https://docs.hardcover.app/api/getting-started/)) *(via search index)*.
- A rich book graph, but beta status and annual token resets make it riskier than Open Library for a graded project.

### 3.4 Recipes / food

#### TheMealDB (recommended)
- The test key `"1"` is listed for development and educational use. A supporter key (via PayPal, price not stated) is needed to release publicly on an app store ([API page](https://www.themealdb.com/api.php)).
- **Endpoints:**
  - `search.php?s=` (name) and `search.php?f=` (first letter)
  - `lookup.php?i=` (ID)
  - `filter.php?i=|c=|a=` (ingredient, category, area)
  - random

  Multi-ingredient filtering and the full listing (beyond 100 items) are premium ([API page](https://www.themealdb.com/api.php)).
- **Images:** Meal image URLs accept `/small`, `/medium` and `/large`. Ingredient images are at `/images/ingredients/<name>.png` ([API page](https://www.themealdb.com/api.php)).
- **Rate limits:** **not documented**. Commercial or storage terms: **not documented** on the API page (a separate Terms page exists).
- **Progress fit:** "Cooked it" status, a rating, and optionally which instruction step you're on.

#### Spoonacular
- Free: **50 points per day** at 1 request per second with 2 concurrent. No credit card needed when signing up directly (RapidAPI requires one). **Backlink required.** **Cache user-requested data for at most 1 hour**, and delete all data if you stop using the API ([pricing](https://spoonacular.com/food-api/pricing)).
- Verdict: the storage rule conflicts with "save items to my list" unless you store only the ID and re-fetch, and 50 points per day is tight.

#### Edamam: ruled out (see §4).

### 3.5 Video games

#### RAWG (recommended for games)
- Free plan: 20,000 requests per month. **A backlink (active hyperlink) is required on every page showing RAWG data.** No data redistribution ([API docs](https://rawg.io/apidocs)).
- The plan box says "Non-commercial projects only", but the ToS allow free commercial use up to 100,000 MAU or 500,000 page views per month. The two official pages conflict ([API docs](https://rawg.io/apidocs); [API ToS](https://rawg.io/tos_api)). A student project is fine under either reading.
- Key via "Get API Key". Data storage: **not documented**.
- **Progress fit:** Hours played or status (playing, beaten, 100%).

#### IGDB
- Auth uses a Twitch app's client ID and secret exchanged for an app access token via `POST https://id.twitch.tv/oauth2/token` with `grant_type=client_credentials`. Limits: 4 requests per second and 8 open requests, with HTTP 429 on excess ([IGDB docs](https://api-docs.igdb.com/)) *(via search index; page returns 403 to fetchers)*.
- The secret must stay server-side ([Twitch register app](https://dev.twitch.tv/docs/authentication/register-app/)).
- The IGDB FAQ says you may store and serve retrieved data locally. Commercial use goes through a partnership and requires visible attribution ([igdb.com/api](https://www.igdb.com/api)) *(via search index)*.
- Richer than RAWG, but the auth setup (Twitch account, token refresh) is extra work.

#### Giant Bomb
- Still active, based on 2026 community posts. The original API terms are non-commercial ([announcement](https://giantbomb.com/articles/giant-bomb-api-now-available)) *(via search index)*. Current rate limits were not verified. Lower priority.

### 3.6 Board games

#### BoardGameGeek XML API2
- Registration is now required for nearly all use. Non-commercial licences are "generally provided at no cost". Approval is discretionary (apps competing with BGG may be denied). Tokens are created on `boardgamegeek.com/applications` after approval ([Using the XML API](https://boardgamegeek.com/using_the_xml_api)) *(via search index; page returns 403)*.
- Terms: **strictly non-commercial**, and you must credit BoardGameGeek by name ([XML API Terms](https://boardgamegeek.com/xmlapi/termsofuse)) *(via search index)*.
- Approval is manual and reportedly takes "a few days" (BGG forum: [registration thread](https://boardgamegeek.com/thread/3525319/registration-to-use-the-xml-api-and-obtain-soon-to)) *(via search index)*.
- XML only, not JSON.
- **Progress fit:** Plays logged.

### 3.7 Music

#### MusicBrainz (recommended for music)
- No API key. A **meaningful User-Agent is required**. Limit is **1 call per second** or your IP may be blocked. Search with `/<entity>?query=&limit=&offset=` and look up by MBID. JSON via `fmt=json` ([MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)).
- Core data is **CC0**. Supplementary data is CC BY-NC-SA 3.0. Cover art comes from the separate Cover Art Archive ([Data licence](https://musicbrainz.org/doc/About/Data_License)).
- **Progress fit:** Tracks listened within an album.

#### Discogs
- Limits: 60 per minute authenticated and 25 per minute unauthenticated, per source IP ([Discogs developers](https://www.discogs.com/developers)) *(via search index)*. Whether search and images require auth was not verified on the current docs. Storage terms not verified.

#### Spotify: avoid (see §1 and §4).

#### Last.fm
- API ToS: data may be used **solely for non-commercial purposes**, and you must cache according to HTTP headers ([Last.fm API ToS](https://www.last.fm/api/tos)) *(via search index)*. Needs an API key. Good for scrobble-style data, but weaker for search → save.

### 3.8 Podcasts

#### Podcast Index
- Sign up by email and receive the key and secret immediately. **Free email domains such as gmail.com are blocked**, so use a school email. The API is free "for any lawful purpose, including commercial use" ([Signup](https://api.podcastindex.org/signup); [ToS](https://api.podcastindex.org/tos_v1.0.html)) *(via search index)*.
- Auth headers: `X-Auth-Key`, `X-Auth-Date`, `Authorization` (SHA-1 of key + secret + date) and `User-Agent`. Search via `search/byterm` ([OpenAPI spec](https://podcastindex-org.github.io/docs-api/pi_api.yaml)) *(via search index)*.
- Rate limits: **not documented** in the sources reached.
- **Progress fit:** Episodes listened.

#### iTunes Search API
- No key. About 20 calls per minute, "subject to change". `term`, `media=podcast|ebook|music|…`, `entity` (e.g. `podcastEpisode`), and `limit` 1–200. ID lookup via `/lookup`. Artwork at 60 and 100 px ([Apple Search API](https://performance-partners.apple.com/search-api)).
- The terms frame the content as **promotional**: show it near a store badge, don't cache previews. The page recommends caching search results for large sites ([Apple Search API](https://performance-partners.apple.com/search-api)). The promotional framing makes it a weaker fit than Podcast Index.

#### Listen Notes: avoid (see §4).

### 3.9 Anime / manga

#### Jikan (unofficial MyAnimeList)
- No auth. **60 requests per minute, 3 per second**, no daily cap. Responses are cached for 24 hours, with ETag support. Data is scraped from public MyAnimeList pages, and MAL itself can still rate-limit you ([Jikan docs](https://docs.api.jikan.moe/); [jikan.moe](https://jikan.moe/)) *(via search index)*.
- MAL IDs are stable keys. Responses include episodes and chapters.
- Risk: because it is unofficial, it can break when MAL changes its pages.

#### AniList
- GraphQL. Normally **90 requests per minute**, but the docs currently say the API "is currently in a degraded state and is limited to 30 requests per minute" ([AniList rate limiting](https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting)).
- Terms:
  - Free for apps earning under $150 per month.
  - The API must not be used as a backup or data store, and bulk collection is banned. Enforcement is relaxed for purely educational projects.
  - Apps using the AniList name must say they are unofficial.

  Source: [AniList ToU](https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/terms-of-use).
- **Progress fit:** Episodes or chapters.

#### MangaDex
- About **5 requests per second** per IP globally. You **must credit MangaDex** (and scanlation groups if chapters are readable). **No ads or paid services** ([Limitations](https://api.mangadex.org/docs/2-limitations/)) *(via search index)*.

#### MyAnimeList official API v2 / Kitsu
- The docs pages render client-side and could not be read. Details are **unverified**, so I did not evaluate them further.

### 3.10 Art / museums

#### The Met Collection API
- No key. Please stay at **80 requests per second** or below.
- `/v1/search` **retired 2026-10-01**. Use `/v1.1/search`, which adds `offset` and `limit` (max 500, offset + limit ≤ 10,000).
- Objects have `objectID`, `primaryImage`, `isPublicDomain` and similar fields. Select datasets are **CC0**.

Source: [Met API](https://metmuseum.github.io/).

#### Art Institute of Chicago
- No key. Anonymous use is throttled to **60 requests per minute**. Most data is CC0, while the `description` field is CC BY 4.0. IIIF images ([AIC API docs](https://api.artic.edu/docs/)) *(via search index)*.

#### Harvard Art Museums
- API key required. About 2,500 calls per day requested. **Non-commercial only.** **Don't cache or store content for more than two weeks** without permission. Show images from the API's own image URLs ([Harvard API docs](https://github.com/harvardartmuseums/api-docs)).

**Progress fit for art:** weak. Use "visited/seen in person", favourites and notes.

### 3.11 National parks

#### NPS Data API
- Free key (pass it as `X-Api-Key` or `api_key`). **1,000 requests per hour.** Exceeding it returns HTTP 429 and a block that lifts after an hour. Keep the key out of public repos ([NPS guides](https://www.nps.gov/subjects/developer/guides.htm)).
- `/api/v1/parks` supports `limit` and zero-based `start`. A `/thingstodo` endpoint was added in July 2020 ([NPS changelog](https://www.nps.gov/subjects/developer/changelog.htm)). A free-text `q` parameter was **not verified** from official docs.
- **Progress fit:** Parks visited, or things-to-do completed.

### 3.12 Beer / breweries

#### Open Brewery DB
- No sign-ups, keys or rate limits. Search is `GET /v1/breweries/search?query=` with `per_page` up to 200. Recommended for personal projects, with no SLA ([Open Brewery DB docs](https://www.openbrewerydb.org/documentation); [FAQ](https://www.openbrewerydb.org/faq)) *(via search index)*.
- No images. These are breweries, not individual beers.

### 3.13 Comics

#### Comic Vine
- API key required. **200 requests per resource per hour**, with velocity detection. **Non-commercial only.** No competing product or redistribution. Link back to Comic Vine ([Comic Vine API](https://comicvine.gamespot.com/api/)).
- **Progress fit:** Issues read within a volume.

---

## 4. Ruled out

| Candidate | Reason | Source |
|-----------|--------|--------|
| Spotify Web API | Development Mode needs Premium, 5 users max, search limit max 10, many endpoints removed (Feb 2026). Extended quota is organizations only (≥250k MAU). | [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes), [Feb 2026 changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026) |
| Marvel Comics API | `developer.marvel.com` 301-redirects to `www.marvel.com` (checked 2026-11-15). The portal appears to be discontinued. | https://developer.marvel.com/ |
| Punk API | `punkapi.com` does not resolve (DNS ENOTFOUND, 2026-11-15). | https://punkapi.com/ |
| Edamam Recipe Search | Paid tiers from $9/month. The free tier appears only on a retired-version page. Terms forbid automated collection. | [Recipe API](https://developer.edamam.com/edamam-recipe-api), [retired page](https://developer.edamam.com/recipe-api) |
| Listen Notes | Free plan: 150 requests/month and suspension on overage. No server-side caching or storage except IDs and dates. "Powered by Listen Notes" logo required. | [Pricing](https://www.listennotes.com/api/pricing/) |
| Spoonacular (as primary) | 50 points/day; 1-hour cache limit conflicts with saving items. | [Pricing](https://spoonacular.com/food-api/pricing) |
| OMDb (as primary) | Posters are patrons-only; CC BY-NC. | [omdbapi.com](https://www.omdbapi.com/) |
| Harvard Art Museums (as primary) | 2-week storage cap; non-commercial. The Met or AIC are freer. | [Docs](https://github.com/harvardartmuseums/api-docs) |
| Kitsu, MAL v2 | Official docs couldn't be read (client-rendered), so terms are unverified. Jikan and AniList cover the domain. | [Kitsu](https://kitsu.docs.apiary.io/), [MAL](https://myanimelist.net/apiconfig/references/api/v2) |

---

## 5. Sources (all accessed 2026-11-15)

- https://www.tvmaze.com/api
- https://developer.themoviedb.org/docs/getting-started
- https://developer.themoviedb.org/docs/rate-limiting
- https://developer.themoviedb.org/docs/authentication-application (via search index)
- https://developer.themoviedb.org/docs/search-and-query-for-details (via search index)
- https://developer.themoviedb.org/docs/faq (via search index)
- https://www.themoviedb.org/api-terms-of-use
- https://www.omdbapi.com/
- https://www.omdbapi.com/apikey.aspx
- https://developer.trakt.tv/docs/rate-limiting (via search index)
- https://developer.trakt.tv/docs/create-an-app (via search index)
- https://openlibrary.org/developers/api
- https://openlibrary.org/dev/docs/api/search
- https://openlibrary.org/dev/docs/api/covers
- https://openlibrary.org/developers/licensing
- https://developers.google.com/books/docs/v1/using
- https://developers.google.com/books/terms
- https://docs.hardcover.app/api/getting-started/ (via search index; 403 to fetch)
- https://www.themealdb.com/api.php
- https://spoonacular.com/food-api/pricing
- https://developer.edamam.com/edamam-recipe-api (via search index)
- https://developer.edamam.com/recipe-api (via search index)
- https://rawg.io/apidocs
- https://rawg.io/tos_api (via search index)
- https://api-docs.igdb.com/ (via search index; 403 to fetch)
- https://www.igdb.com/api (via search index)
- https://dev.twitch.tv/docs/authentication/register-app/ (via search index)
- https://giantbomb.com/articles/giant-bomb-api-now-available (via search index)
- https://boardgamegeek.com/using_the_xml_api (via search index; 403 to fetch)
- https://boardgamegeek.com/xmlapi/termsofuse (via search index)
- https://boardgamegeek.com/thread/3525319/registration-to-use-the-xml-api-and-obtain-soon-to (via search index)
- https://musicbrainz.org/doc/MusicBrainz_API
- https://musicbrainz.org/doc/About/Data_License
- https://www.discogs.com/developers (via search index; 403 to fetch)
- https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- https://developer.spotify.com/documentation/web-api/references/changes/february-2026
- https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates (via search index)
- https://www.last.fm/api/tos (via search index)
- https://api.podcastindex.org/signup (via search index)
- https://api.podcastindex.org/tos_v1.0.html (via search index; 403 to fetch)
- https://podcastindex-org.github.io/docs-api/pi_api.yaml (via search index)
- https://performance-partners.apple.com/search-api
- https://www.listennotes.com/api/pricing/
- https://docs.api.jikan.moe/ (via search index)
- https://jikan.moe/ (via search index)
- https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting
- https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/terms-of-use
- https://api.mangadex.org/docs/2-limitations/ (via search index)
- https://metmuseum.github.io/
- https://api.artic.edu/docs/ (via search index; 403 to fetch)
- https://github.com/harvardartmuseums/api-docs
- https://www.nps.gov/subjects/developer/guides.htm
- https://www.nps.gov/subjects/developer/changelog.htm (via search index)
- https://www.openbrewerydb.org/documentation (via search index; 403 to fetch)
- https://www.openbrewerydb.org/faq (via search index)
- https://comicvine.gamespot.com/api/
- https://developer.marvel.com/ (301 → www.marvel.com)
- https://punkapi.com/ (DNS failure)
- https://kitsu.docs.apiary.io/ (unreadable)
- https://myanimelist.net/apiconfig/references/api/v2 (unreadable)
