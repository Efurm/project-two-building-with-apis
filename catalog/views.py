from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import tmdb

OVERVIEW_LENGTH = 150


def _format_result(movie):
    """Turn one TMDB search result into what the results template shows."""
    overview = (movie.get("overview") or "No overview available.").replace("\n", " ")
    if len(overview) > OVERVIEW_LENGTH:
        overview = overview[:OVERVIEW_LENGTH].rstrip() + "…"
    return {
        "tmdb_id": movie.get("id"),
        "title": movie.get("title") or "(untitled)",
        "year": (movie.get("release_date") or "")[:4],
        "overview": overview,
        "poster_url": tmdb.poster_url(movie.get("poster_path")),
    }


@login_required
def find_movies(request):
    """Search TMDB. HTMX requests get only the results partial; others get the full page."""
    query = request.GET.get("q", "").strip()
    context = {"query": query, "results": [], "error": None}
    if query:
        try:
            data = tmdb.search_movies(query)
        except tmdb.TMDBError as error:
            context["error"] = error.message
        else:
            context["results"] = [_format_result(movie) for movie in data.get("results", [])]

    template = "catalog/partials/results.html" if request.htmx else "catalog/find.html"
    return render(request, template, context)
