"""Views for a user's named lists (owner-only in this phase).

Every lookup is scoped to the requesting user, so other users' lists and entries
look like they don't exist (404).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRedirect

from .browse import browse_context
from .forms import MovieListForm
from .models import Entry, ListItem, MovieList


def _own_list(request, pk):
    return get_object_or_404(MovieList, pk=pk, owner=request.user)


def _own_entry(request, pk):
    return get_object_or_404(Entry.objects.select_related("movie"), pk=pk, user=request.user)


def entry_lists_context(entry):
    """What the entry page's "In lists" panel needs: the lists it is in, and the rest."""
    lists = MovieList.objects.filter(owner=entry.user)
    member_ids = set(entry.list_items.values_list("movie_list_id", flat=True))
    return {
        "entry": entry,
        "member_lists": [lst for lst in lists if lst.pk in member_ids],
        "other_lists": [lst for lst in lists if lst.pk not in member_ids],
    }


def _entry_lists_panel(request, entry):
    return render(request, "lists/partials/entry_lists.html", entry_lists_context(entry))


@login_required
def list_index(request):
    """GET: the user's lists and a "new list" form. POST: create a list."""
    form = MovieListForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        movie_list = form.save(commit=False)
        movie_list.owner = request.user
        movie_list.save()
        messages.success(request, f"Created “{movie_list.name}”.")
        return redirect("lists:detail", pk=movie_list.pk)
    lists = MovieList.objects.filter(owner=request.user).annotate(item_count=Count("items"))
    return render(request, "lists/index.html", {"lists": lists, "form": form})


@login_required
def list_detail(request, pk):
    """A list's entries with the same search, filters, sorts, and pagination as the library."""
    movie_list = _own_list(request, pk)
    entries = Entry.objects.filter(list_items__movie_list=movie_list).select_related("movie")
    context = browse_context(request, entries, reverse("lists:detail", args=[pk]))
    context.update(
        {
            "movie_list": movie_list,
            "card_template": "lists/partials/list_entry_card.html",
            "empty_message": "This list is empty. Add movies from their pages in your library.",
        }
    )
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "library/partials/browse.html", context)
    return render(request, "lists/detail.html", context)


@login_required
def rename_list(request, pk):
    """GET: the rename form. POST: rename and return the list header (or the form with errors)."""
    movie_list = _own_list(request, pk)
    form = MovieListForm(request.POST or None, instance=movie_list)
    if request.method == "POST" and form.is_valid():
        form.save()
        if not request.htmx:
            return redirect("lists:detail", pk=pk)
        return render(request, "lists/partials/list_header.html", {"movie_list": movie_list})
    if not request.htmx:
        return render(request, "lists/rename.html", {"movie_list": movie_list, "form": form})
    return render(
        request, "lists/partials/rename_form.html", {"movie_list": movie_list, "form": form}
    )


@login_required
def delete_list(request, pk):
    """GET: confirm. POST: delete the list. Its items go with it; the entries stay."""
    movie_list = _own_list(request, pk)
    if request.method == "POST":
        name = movie_list.name
        movie_list.delete()
        messages.success(
            request, f"Deleted the list “{name}”. Its movies are still in your library."
        )
        if request.htmx:
            return HttpResponseClientRedirect(reverse("lists:index"))
        return redirect("lists:index")
    context = {"movie_list": movie_list, "item_count": movie_list.items.count()}
    template = "lists/partials/delete_confirm.html" if request.htmx else "lists/delete.html"
    return render(request, template, context)


@login_required
@require_POST
def add_item(request, pk):
    """Add one of the user's own entries to one of their lists; returns the entry's panel.

    Another user's entry is treated as nonexistent (404), so lists only ever hold the
    owner's own data. Adding an entry that is already in the list changes nothing.
    """
    movie_list = _own_list(request, pk)
    entry = _own_entry(request, request.POST.get("entry"))
    try:
        with transaction.atomic():
            ListItem.objects.create(movie_list=movie_list, entry=entry)
    except IntegrityError:
        pass  # Already in this list (unique list + entry).
    if not request.htmx:
        return redirect("library:entry_detail", pk=entry.pk)
    return _entry_lists_panel(request, entry)


@login_required
@require_POST
def remove_item(request, pk, entry_pk):
    """Remove an entry from a list (the entry stays in the library).

    From the entry page (`panel=1`) returns the updated "In lists" panel; from the list
    page returns an empty response so HTMX can drop the card.
    """
    movie_list = _own_list(request, pk)
    entry = _own_entry(request, entry_pk)
    ListItem.objects.filter(movie_list=movie_list, entry=entry).delete()
    if request.POST.get("panel"):
        if not request.htmx:
            return redirect("library:entry_detail", pk=entry.pk)
        return _entry_lists_panel(request, entry)
    if not request.htmx:
        return redirect("lists:detail", pk=pk)
    return HttpResponse("")
