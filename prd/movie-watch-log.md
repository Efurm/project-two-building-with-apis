# PRD: Movie Watch Log

## Problem Statement

I watch a lot of movies, and I lose track of what I've seen, what I want to see, and what I thought of each one. Streaming apps only remember what I watched on that one service, and a notes app has no movie details, posters, or way to sort and filter. I also want to group movies into my own lists (for example "Date night" or "Best horror") and decide for each list whether it stays private, is public for anyone to see, or is shared only with specific friends.

I need this to keep working when the movie database I search with is down. Once I've saved a movie, my notes, ratings, and lists should still be there and still browsable. When a lookup does fail, I want to be told clearly what went wrong instead of seeing a broken page.

I also want to reach my data programmatically, through an API that respects the same privacy rules as the website.

## Solution

A Django web application where a signed-in user searches The Movie Database (TMDB), saves movies to a personal **library**, and records their own status, 1–5 star rating, notes, date watched, and times watched for each one. When a movie is saved, its TMDB details (title, overview, runtime, genres, release date, score, poster reference) are copied into the app's own SQLite database. After that, the library works without TMDB.

Users browse their library with search, filters, sorting, and pagination, all running on local data. They can organize library entries into any number of **named lists**. Each list is Private, Public (readable by anyone, including logged-out visitors), or Shared (readable only by usernames the owner chooses). Public lists appear on the owner's profile page, and shared lists appear on the recipient's "Shared with me" page.

The application also provides a REST API (Django REST Framework) for listing, creating, updating, and deleting entries and lists. The API enforces the same visibility rules as the website. It can be used with the website login session or with a personal API token.

When TMDB is unavailable or a request fails, the app shows a specific, useful message: timeout, cannot connect, token rejected, rate limited, or provider error. Already-saved data is never affected.

## User Stories

### Accounts and sign-in

1. As a visitor, I want to create an account with a username and password, so that I can start saving movies.
2. As a user, I want to sign in and sign out, so that only I can manage my saved data.
3. As a signed-in user, I want a "My account" page where I can generate or regenerate a personal API token, so that I can use the API from scripts or tools like curl.
4. As a visitor who is not signed in, I want to be redirected to sign in when I try to manage data, so that I understand why I can't make changes.

### Finding and saving movies (TMDB)

5. As a signed-in user, I want a "Find movies" page with a search box, so that I can look up movies on TMDB.
6. As a signed-in user, I want search results to show the poster, title, year, and a short overview, so that I can identify the right movie.
7. As a signed-in user, I want search results to load without a full page reload, so that searching feels quick.
8. As a signed-in user, I want to save a result with one click and choose its initial status ("Want to watch" or "Watched") from a small dropdown, so that I can log a movie I just watched without an extra form.
9. As a signed-in user, I want the Save button to change to "In library ✓" after saving, so that I know it worked.
10. As a signed-in user, I want movies already in my library to show as "In library ✓" in search results, so that I don't try to save duplicates.
11. As a signed-in user, I want to be prevented from saving the same movie twice, so that my library has no duplicates.
12. As a signed-in user, I want a clear message when my search finds no movies, so that I know to try different words.
13. As a signed-in user, I want a clear message when TMDB times out, cannot be reached, rejects the app's credentials, rate-limits the app, or returns an error, so that I understand the problem isn't my fault and can try again later.
14. As a signed-in user, I want saving to still work for a movie that is already stored locally even if TMDB is down, so that I'm not blocked unnecessarily.

### Editing my own information

15. As a signed-in user, I want to set an entry's status to Want to watch, Watching, or Watched, so that I can track my progress.
16. As a signed-in user, I want to give a watched movie a rating from 1 to 5 whole stars, or leave it unrated, so that I can record my opinion.
17. As a signed-in user, I want rating to be possible only once a movie is marked Watched, so that I don't rate movies I haven't seen.
18. As a signed-in user, I want to record the date I watched a movie and how many times I've watched it, so that I can track rewatches.
19. As a signed-in user, I want the rating, date watched, and times watched to be cleared when I change a movie's status away from Watched, so that my data stays consistent.
20. As a signed-in user, I want to write plain-text notes on any entry, so that I can remember my thoughts.
21. As a signed-in user, I want to edit an entry in place on its page, without navigating to a separate form page, so that editing feels fast.
22. As a signed-in user, I want validation errors to appear next to the fields in the edit form, so that I can fix mistakes easily.
23. As a signed-in user, I want to change a movie's status directly from its card in my library, so that quick updates take one click.
24. As a signed-in user, I want to delete an entry after a confirmation that tells me how many of my lists it will be removed from, so that I don't lose list placements by accident.

### Browsing my library (local data only)

25. As a signed-in user, I want to browse my library even when TMDB is down, so that my saved data is always available.
26. As a signed-in user, I want to search my library by title or by the text of my notes, so that I can find a movie quickly.
27. As a signed-in user, I want to filter my library by status, genre, minimum star rating, and release decade, so that I can narrow down what I see.
28. As a signed-in user, I want to sort my library by date added, title, my rating, release date, or date watched, ascending or descending, so that I can view it in the order I need.
29. As a signed-in user, I want unrated movies to appear last when sorting by rating in either direction, so that rated movies stay at the top.
30. As a signed-in user, I want my library paginated at 20 movies per page, so that large libraries stay fast and readable.
31. As a signed-in user, I want filter, sort, and page changes to update the results without a full page reload, so that browsing feels smooth.
32. As a signed-in user, I want my filters, sort, and page to be reflected in the URL, so that I can bookmark a view and use the back button.
33. As a signed-in user, I want saved movies to show a placeholder image when the poster cannot load, so that the page still looks tidy when TMDB's image server is unavailable.

### Keeping movie data fresh

34. As a signed-in user, I want a "Refresh from TMDB" button on an entry's page, so that I can update that movie's details.
35. As a signed-in user, I want a failed refresh to keep the existing stored details and show me why it failed, so that nothing is lost.
36. As the site operator, I want a management command that refreshes movies whose stored data is older than a given number of days (default 180), so that the app complies with TMDB's requirement to refresh cached data at least every 6 months.

### Named lists

37. As a signed-in user, I want to create, rename, and delete named lists, so that I can organize my movies by theme.
38. As a signed-in user, I want to add my library entries to a list and remove them from it, so that a list contains exactly the movies I choose.
39. As a signed-in user, I want the same movie to be able to appear in several of my lists, so that I can categorize it in more than one way.
40. As a signed-in user, I want to only be able to add my own entries to my lists, so that lists can't contain other people's data.
41. As a signed-in user, I want deleting a list to leave the movies in my library, so that I don't lose entries by removing a list.
42. As a signed-in user, I want to browse a list with the same search, filter, sort, and pagination controls as my library, so that large lists are easy to use.
43. As a list viewer, I want to see each movie's status, rating, and notes in a list I'm allowed to view, so that I understand the owner's opinions.

### Privacy and sharing

44. As a signed-in user, I want my library as a whole to always be private, so that only movies I deliberately put in a visible list are ever shown to others.
45. As a list owner, I want to set each list to Private, Public, or Shared, so that I control who can see it.
46. As a list owner, I want to share a list with specific users by username, and remove them later, so that I can choose exactly who sees it.
47. As a list owner, I want an error if I try to share with a username that doesn't exist, so that I don't share with a typo.
48. As a visitor who is not signed in, I want to view any public list and any user's profile page of public lists, so that public really means public.
49. As a signed-in user, I want a "Shared with me" page listing lists others have shared with me, so that I can find them without asking for a link.
50. As anyone, I want a list I'm not allowed to see to look like it doesn't exist (not found), so that private lists cannot be discovered.
51. As a viewer of someone else's list, I want to be unable to edit, add to, remove from, or delete it, so that only the owner controls it.

### API

52. As an API user, I want to authenticate with my website session or my personal API token, so that I can use the API from the browser or from scripts.
53. As an API user, I want to list my library entries with the same search, filter, sort, and pagination parameters as the website, so that I can get exactly the data I need.
54. As an API user, I want to create an entry by sending a TMDB id plus optional status, rating, notes, date watched, and times watched, so that I can save movies without the website.
55. As an API user, I want a 503 response with a clear message when creating an entry needs TMDB and TMDB is unavailable, so that my client can explain the problem and retry later.
56. As an API user, I want to update and delete my entries, so that I can manage my data programmatically.
57. As an API user, I want the API to enforce the same rating and status rules as the website, so that data stays consistent however it is entered.
58. As an API user, I want to list, create, update, and delete my lists, including their visibility and the usernames they're shared with, so that I can manage sharing programmatically.
59. As an API user, I want to add and remove entries in a list through the API, so that I can organize lists programmatically.
60. As an API user, I want to filter lists to those shared with me or owned by a given username, so that the API mirrors the "Shared with me" and profile pages.
61. As an anonymous API user, I want read-only access to public lists, so that public data is reachable without an account.
62. As an API user, I want lists I'm not allowed to see to return 404 and write attempts on others' lists to be refused, so that the API is as private as the website.

## Implementation Decisions

### Stack

- Django, Django REST Framework, SQLite, managed with uv. Ruff for linting and formatting.
- Tailwind CSS with DaisyUI, built by Tailwind's standalone command-line executable with the DaisyUI plugin, so Node.js and npm are not required. The built stylesheet is committed so the project runs without a build step.
- HTMX is stored as a local static file, not loaded from a CDN, plus the `django-htmx` package so views can detect HTMX requests.
- pytest with pytest-django for tests. Ruff, pytest, and pytest-django are development dependencies.
- The TMDB Read Access Token and Django's secret key come from the git-ignored `.env` file, loaded with uv's env-file option, consistent with the existing console script.

### Project structure

- A project settings package named `config` and three apps:
  - **accounts**: sign-up (Django's built-in user creation form), login/logout (Django's built-in auth views), and the "My account" page with API token generation and regeneration.
  - **catalog**: everything that talks to TMDB. The `Movie` and `Genre` models, a TMDB client module, the shared "get or fetch movie" service, the "Find movies" search page, the save action, the refresh action, and the refresh management command.
  - **library**: the `Entry`, `MovieList`, and `ListItem` models, sharing, the library browse page, entry pages, list pages, profile pages, "Shared with me", and the DRF API.
- The project uses Django's default User model.

### Models

- **Genre**: TMDB genre id and name.
- **Movie** (shared by all users, one row per TMDB id): TMDB id (unique), title, original title, release date (nullable), overview, runtime in minutes (nullable), TMDB vote average, poster path (nullable), genres (many-to-many to Genre), and a last-fetched timestamp. It stores the poster path, not the image. Full poster URLs are built when pages render.
- **Entry** (one user's copy of one movie): user, movie, status (Want to watch / Watching / Watched as text choices, default Want to watch), rating (small integer 1–5, nullable), notes (plain text, blank allowed), date watched (nullable), times watched (non-negative integer), and created/updated timestamps. A user can have only one entry per movie (unique constraint on user + movie).
- **Cross-field rule** on Entry: rating, date watched, and times watched greater than zero are allowed only when status is Watched. The rule is defined once on the model and enforced by both the website form and the API serializer. When status changes away from Watched, those three fields are cleared.
- **MovieList**: owner, name, visibility (Private / Public / Shared as text choices, default Private), `shared_with` (many-to-many to User), and timestamps.
- **ListItem**: list, entry, and date added. Each entry can appear in a list only once. Items are ordered by date added by default.
- **Delete behavior**: deleting an Entry cascades to its ListItems. Deleting a MovieList cascades to its ListItems but never to Entries. Movie rows left with no entries are kept.

### Visibility rules (single source of truth)

- A user's library (entries) is always private: only its owner can see or change it, on the website or through the API.
- A list is visible to its owner, to anyone if Public, and to the owner and the `shared_with` users if Shared.
- Only the owner can modify a list, its items, its visibility, or its sharing.
- These rules live in one place: a queryset method on MovieList that returns the lists visible to a given user (anonymous users included), plus a matching DRF object permission for write actions. Website views and API views both use them.
- A list the viewer may not see returns 404, not 403, on both the website and the API.
- Only existing usernames can be added to `shared_with`. Only the owner's own entries can be added to their lists.

### TMDB integration

- Only three operations ever call TMDB: **search**, **save** (fetching details for a movie not yet stored), and **refresh**. All browsing, filtering, list viewing, profile pages, and API reads use local data only.
- A single TMDB client module makes all requests, with a timeout, and turns failures into specific, user-readable errors: timeout, connection failure, rejected token (401), rate limited (429), other HTTP errors, and invalid JSON. The messages follow the existing console script.
- A shared "get or fetch movie" service, used by both the website save action and the API create endpoint, returns the stored Movie if it exists. Otherwise it fetches TMDB's movie-details endpoint and creates the Movie and its Genres. If TMDB fails and the movie isn't stored, it raises a provider-unavailable error.
- Search runs only when the user submits (Enter or button), not as they type.
- The website shows TMDB failures as a DaisyUI alert inside the HTMX-swapped results area. The API returns 503 with a `detail` message.
- Refresh updates the stored Movie and Genres and its last-fetched timestamp. If refresh fails, the stored data is unchanged and the user sees an alert.
- The refresh management command accepts a "older than N days" option, default 180.
- Poster images load from TMDB's image CDN. If an image fails to load, the page shows a placeholder.
- The website shows TMDB attribution, as TMDB's terms require.

### Website pages and interactions

- **Find movies**: a search form whose results grid is swapped in by HTMX. Each result has a Save button with a status dropdown ("Want to watch" / "Watched"). Saving swaps the button to "In library ✓". Results already in the user's library show that state from the start.
- **Library**: a paginated grid or list of entry cards, 20 per page.
  - Search covers movie title and the user's notes.
  - Filters: status, genre, minimum rating (whole stars), and release decade.
  - Sorts: date added, title, rating, release date, and date watched, ascending or descending. Unrated entries come last in either rating direction.
  - All parameters live in the URL query string. Changing them triggers an HTMX swap of the results and updates the browser URL.
  - Each card has a status control that updates in place.
- **Entry page**: shows the movie details, with poster and placeholder fallback, and the user's data. **Edit** swaps in the entry form via HTMX, and **Save** posts the form and swaps back the updated panel, or the form with errors. A single entry form holds the cross-field rules. Views return a full page for normal requests and a partial for HTMX requests.
  - The rating uses DaisyUI's star rating component, with 1–5 whole stars and a clear option. It is disabled unless status is Watched. This look was chosen in the rating prototype.
  - **Refresh from TMDB** is an HTMX action showing a success or failure alert.
  - **Delete** uses a confirmation modal that states how many lists the entry will be removed from.
- **Lists**: pages to create, rename, delete, and set the visibility of lists, manage `shared_with` usernames, and add or remove entries. A list's detail page reuses the library's search, filter, sort, and pagination behavior, scoped to that list's entries, and shows each entry's status, rating, and notes.
- **Profile page** (by username): the user's public lists. It can be viewed without signing in.
- **Shared with me**: the lists other users have shared with the signed-in user.
- **Accounts**: sign-up, login, logout, and "My account" with token generation.
- All pages that manage data require sign-in. Public lists and profile pages do not.

### API (Django REST Framework)

- Authentication: session authentication and DRF's built-in token authentication.
- **Entries resource**: list, create, retrieve, update (full and partial), and delete, limited to the requesting user's own entries.
  - Listing accepts the same search, filter, sort, and page parameters as the website library page, and is paginated at 20 per page.
  - Create takes a TMDB id plus optional user fields and uses the shared "get or fetch movie" service. It returns 503 with a message if TMDB is needed and unavailable, and rejects a movie that is already in the library.
  - Delete returns 204 and cascades to list items.
  - Responses include the nested stored movie details.
- **Lists resource**: list, create, retrieve, update, and delete.
  - Listing returns lists visible to the requester. Filters cover "shared with me" and "owner username".
  - Writable fields include name, visibility, and `shared_with` given as usernames.
  - Unknown usernames are rejected.
- **List items** (nested under a list): list, add (by entry id, own entries only), and remove.
- Anonymous requests may only read public lists and their items. All writes require authentication and ownership.
- Serializer validation enforces the same status, rating, and date rules as the website form.

### Testing approach

- pytest fixtures for users (owner, shared user, stranger), anonymous and authenticated clients, an API client, and sample movies, entries, and lists.
- The TMDB client is always replaced with fakes in tests. Real network calls never run during tests.
- Visibility is tested as a parametrized matrix: viewer (owner, shared user, stranger, anonymous) × list visibility (private, public, shared) × surface (website, API) × action (read, write).

## Out of Scope

- TV shows, episodes, or any media other than movies.
- Named-list features beyond basic membership: manual reordering of list items, list descriptions, cover images, or collaborative editing by shared users.
- Secret or unlisted share links. Sharing is by username only.
- A global "Explore all public lists" page.
- Per-entry visibility or a public view of a user's whole library.
- A "Dropped" status, half-star ratings, or minutes-watched progress.
- Downloading or storing poster images locally.
- Automatic refresh of stale movie data on page view. Refresh is manual or by command only.
- An API endpoint that forwards searches to TMDB. API clients must supply a TMDB id.
- Creating movies from client-supplied data without TMDB.
- Search-as-you-type on the Find movies page.
- Soft delete or undo of deleted entries.
- JWT authentication, OAuth, social login, password reset by email, and email verification.
- Markdown or rich-text notes.
- Runtime-range filters, multi-genre combined filters, filtering the library by list membership, and a page-size picker.
- Node.js or npm tooling.
- Deployment and production hosting.

## Further Notes

- The existing console script that searches TMDB already handles timeouts, connection errors, 401, 429, other HTTP errors, and invalid JSON. Its logic and messages should be carried into the TMDB client module.
- TMDB's free key is for non-commercial use only. It requires visible attribution, and cached data must be refreshed at least every 6 months (see the research document in the repo). The refresh command with a 180-day default exists to meet this requirement.
- The rating appearance was chosen through a throwaway prototype comparing whole stars, half stars, and a 1–10 score. Whole stars were chosen for simple validation, clean "N★ & up" filters, and DaisyUI's built-in rating component.
- The uncommitted dependency changes (Django and DRF added to the project) are the starting point for implementation.
- Every website page that makes a TMDB call must also work, with a helpful message, when TMDB fails. Every other page must work with no network access to TMDB at all.
