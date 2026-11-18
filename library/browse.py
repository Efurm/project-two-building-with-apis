"""Search, filter, sort, and paginate entries from query-string parameters.

Shared by the library page, list pages, and the API. Works on local data only.
Unknown or invalid parameter values are ignored rather than raising errors.
"""

import datetime

from django.core.paginator import Paginator
from django.db.models import F, Q
from django.db.models.functions import Lower

from catalog.models import Genre

from .models import Entry

PAGE_SIZE = 20

# sort key -> label, ordering expression, default direction. Ties fall back to
# newest-added first so every ordering is stable.
SORTS = {
    "added": {"label": "Date added", "field": F("created_at"), "default_dir": "desc"},
    "title": {"label": "Title", "field": Lower("movie__title"), "default_dir": "asc"},
    "rating": {"label": "My rating", "field": F("rating"), "default_dir": "desc"},
    "released": {"label": "Release date", "field": F("movie__release_date"), "default_dir": "desc"},
    "watched": {"label": "Date watched", "field": F("date_watched"), "default_dir": "desc"},
}
DEFAULT_SORT = "added"


def _int(value, minimum=None, maximum=None):
    """`value` as an int within [minimum, maximum], or None if missing/invalid."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
        return None
    return number


def clean_params(params):
    """Validated browse parameters from a QueryDict; invalid values become None/defaults.

    q: text in title or notes. status: an Entry.Status value. genre: TMDB genre id.
    min_rating: 1-5 ("N stars and up"). decade: e.g. 1980 = 1980-1989.
    sort: a SORTS key. dir: "asc" or "desc" (default depends on sort).
    """
    sort = params.get("sort")
    if sort not in SORTS:
        sort = DEFAULT_SORT
    direction = params.get("dir")
    if direction not in ("asc", "desc"):
        direction = SORTS[sort]["default_dir"]
    decade = _int(params.get("decade"), minimum=1870, maximum=2990)
    status = params.get("status")
    return {
        "q": (params.get("q") or "").strip(),
        "status": status if status in Entry.Status.values else None,
        "genre": _int(params.get("genre"), minimum=1),
        "min_rating": _int(params.get("min_rating"), minimum=1, maximum=5),
        "decade": decade if decade is not None and decade % 10 == 0 else None,
        "sort": sort,
        "dir": direction,
    }


def browse_entries(queryset, params):
    """Return `queryset` searched, filtered, and sorted according to `params` (a QueryDict)."""
    p = clean_params(params)
    if p["q"]:
        queryset = queryset.filter(Q(movie__title__icontains=p["q"]) | Q(notes__icontains=p["q"]))
    if p["status"]:
        queryset = queryset.filter(status=p["status"])
    if p["genre"] is not None:
        queryset = queryset.filter(movie__genres__tmdb_id=p["genre"])
    if p["min_rating"] is not None:
        queryset = queryset.filter(rating__gte=p["min_rating"])
    if p["decade"] is not None:
        queryset = queryset.filter(
            movie__release_date__gte=datetime.date(p["decade"], 1, 1),
            movie__release_date__lte=datetime.date(p["decade"] + 9, 12, 31),
        )

    # Missing values (unrated, no release date, no date watched) always sort last.
    field = SORTS[p["sort"]]["field"]
    primary = field.asc(nulls_last=True) if p["dir"] == "asc" else field.desc(nulls_last=True)
    return queryset.order_by(primary, "-created_at", "-pk")


def filter_options(queryset):
    """Genres and decades present in `queryset` (the unfiltered entries being browsed)."""
    genres = Genre.objects.filter(movies__entries__in=queryset).distinct().order_by("name")
    years = queryset.exclude(movie__release_date=None).values_list(
        "movie__release_date__year", flat=True
    )
    decades = sorted({year // 10 * 10 for year in years}, reverse=True)
    return {"genres": genres, "decades": decades}


def browse_context(request, queryset, browse_url):
    """Everything the shared browse template needs: one page of results plus the controls.

    `queryset` is the unfiltered set being browsed (e.g. the user's entries).
    """
    page_obj = Paginator(browse_entries(queryset, request.GET), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    current = {k: "" if v is None else str(v) for k, v in clean_params(request.GET).items()}
    return {
        "page_obj": page_obj,
        "entries": page_obj.object_list,
        "browse_url": browse_url,
        "has_any": queryset.exists(),
        "options": filter_options(queryset),
        "status_choices": Entry.Status.choices,
        "sorts": [(key, spec["label"]) for key, spec in SORTS.items()],
        "current": current,
    }
