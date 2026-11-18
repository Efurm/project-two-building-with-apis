from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EntryForm, EntryStatusForm
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


def _own_entry(request, pk):
    """The requesting user's entry, or 404 (other users' entries look like they don't exist)."""
    return get_object_or_404(
        Entry.objects.select_related("movie").prefetch_related("movie__genres"),
        pk=pk,
        user=request.user,
    )


def _detail_page(request, entry, form=None):
    return render(request, "library/entry_detail.html", {"entry": entry, "form": form})


@login_required
def entry_detail(request, pk):
    """The entry page. HTMX requests (e.g. Cancel) get just the read-only panel."""
    entry = _own_entry(request, pk)
    if request.htmx:
        return render(request, "library/partials/entry_panel.html", {"entry": entry})
    return _detail_page(request, entry)


@login_required
def entry_edit(request, pk):
    """GET: the edit form. POST: save and return the panel, or the form with errors.

    HTMX requests get partials swapped into the page; other requests get full pages.
    """
    entry = _own_entry(request, pk)
    if request.method == "POST":
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            if not request.htmx:
                return redirect("library:entry_detail", pk=entry.pk)
            return render(request, "library/partials/entry_panel.html", {"entry": entry})
    else:
        form = EntryForm(instance=entry)
    if not request.htmx:
        return _detail_page(request, entry, form)
    return render(request, "library/partials/entry_form.html", {"entry": entry, "form": form})


@login_required
@require_POST
def entry_status(request, pk):
    """Change status from a library card; returns the updated card.

    Saving through the form runs `Entry.clean()`, so leaving Watched clears the
    watched-only fields here too.
    """
    entry = _own_entry(request, pk)
    form = EntryStatusForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
    else:
        entry.refresh_from_db()
    if not request.htmx:
        return redirect("library:index")
    return render(
        request, "library/partials/entry_card.html", {"entry": entry, "status_error": form.errors}
    )
