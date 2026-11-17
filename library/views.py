from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def library_index(request):
    """The signed-in user's library. Entries arrive in a later phase."""
    return render(request, "library/index.html")
