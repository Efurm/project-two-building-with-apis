from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Entry


@login_required
def library_index(request):
    """The signed-in user's library, from local data only (never calls TMDB)."""
    entries = (
        Entry.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-created_at", "-pk")
    )
    return render(request, "library/index.html", {"entries": entries})
