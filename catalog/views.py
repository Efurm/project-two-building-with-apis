from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from library.models import Entry

from . import services, tmdb
from .models import Movie

OVERVIEW_LENGTH = 150

# The initial statuses offered by the Save dropdown.
SAVE_STATUSES = (Entry.Status.WANT_TO_WATCH, Entry.Status.WATCHED)


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
            results = [_format_result(movie) for movie in data.get("results", [])]
            saved_ids = set(
                Entry.objects.filter(
                    user=request.user, movie__tmdb_id__in=[r["tmdb_id"] for r in results]
                ).values_list("movie__tmdb_id", flat=True)
            )
            for result in results:
                result["in_library"] = result["tmdb_id"] in saved_ids
            context["results"] = results

    template = "catalog/partials/results.html" if request.htmx else "catalog/find.html"
    return render(request, template, context)


@login_required
@require_POST
def save_movie(request, tmdb_id):
    """Save a TMDB movie to the user's library with the chosen initial status.

    Uses the locally stored Movie when there is one, so TMDB is contacted only for
    movies not stored yet.
    """
    status = request.POST.get("status")
    if status not in SAVE_STATUSES:
        status = Entry.Status.WANT_TO_WATCH

    try:
        movie = services.get_or_fetch_movie(tmdb_id)
    except tmdb.TMDBError as error:
        # Not stored locally and TMDB failed: keep the Save button and explain why.
        if not request.htmx:
            return render(request, "catalog/find.html", {"query": "", "error": error.message})
        return render(
            request,
            "catalog/partials/save_button.html",
            {"tmdb_id": tmdb_id, "in_library": False, "error": error.message},
        )

    try:
        with transaction.atomic():
            Entry.objects.create(user=request.user, movie=movie, status=status)
    except IntegrityError:
        pass  # Already in the library (unique user + movie); keep the existing entry as is.

    if not request.htmx:
        return redirect("library:index")
    return render(
        request,
        "catalog/partials/save_button.html",
        {"tmdb_id": tmdb_id, "in_library": True},
    )


@login_required
@require_POST
def refresh_movie(request, tmdb_id):
    """Refresh a movie in the user's library from TMDB and return its details section.

    On failure the stored movie is unchanged and an alert explains why.
    """
    movie = get_object_or_404(Movie, tmdb_id=tmdb_id, entries__user=request.user)
    context = {"movie": movie}
    try:
        services.refresh_movie(movie)
    except tmdb.TMDBError as error:
        context["refresh_error"] = error.message
    else:
        context["refresh_success"] = True

    if not request.htmx:
        if "refresh_error" in context:
            messages.error(request, f"Could not refresh from TMDB: {context['refresh_error']}")
        else:
            messages.success(request, "Updated from TMDB.")
        entry = Entry.objects.get(user=request.user, movie=movie)
        return redirect("library:entry_detail", pk=entry.pk)
    return render(request, "catalog/partials/movie_details.html", context)
