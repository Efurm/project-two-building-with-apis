from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect

from .browse import browse_context
from .forms import EntryForm, EntryStatusForm
from .list_views import entry_lists_context
from .models import Entry


@login_required
def library_index(request):
    """The signed-in user's library, from local data only (never calls TMDB)."""
    entries = Entry.objects.filter(user=request.user).select_related("movie")
    context = browse_context(request, entries, reverse("library:index"))
    return render(request, _browse_template(request, "library/index.html"), context)


def _browse_template(request, full_page_template):
    """HTMX swaps (but not history restores) get only the shared browse partial."""
    if request.htmx and not request.htmx.history_restore_request:
        return "library/partials/browse.html"
    return full_page_template


def _own_entry(request, pk):
    """The requesting user's entry, or 404 (other users' entries look like they don't exist)."""
    return get_object_or_404(
        Entry.objects.select_related("movie").prefetch_related("movie__genres"),
        pk=pk,
        user=request.user,
    )


def _detail_page(request, entry, form=None):
    context = {"form": form, **entry_lists_context(entry)}
    return render(request, "library/entry_detail.html", context)


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


@login_required
def entry_delete(request, pk):
    """GET: confirm deleting an entry, saying how many lists it is in. POST: delete it.

    Deleting an entry cascades to its list items; the lists themselves stay.
    """
    entry = _own_entry(request, pk)
    if request.method == "POST":
        title = entry.movie.title
        entry.delete()
        messages.success(request, f"Deleted “{title}” from your library.")
        if request.htmx:
            return HttpResponseClientRedirect(reverse("library:index"))
        return redirect("library:index")
    context = {"entry": entry, "list_count": entry.list_items.count()}
    if request.htmx:
        return render(request, "library/partials/entry_delete_confirm.html", context)
    return render(request, "library/entry_delete.html", context)
