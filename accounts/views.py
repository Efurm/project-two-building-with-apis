from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from rest_framework.authtoken.models import Token


def signup(request):
    """Create an account with Django's built-in form, sign the user in, go to the library."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("library:index")
    else:
        form = UserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def my_account(request):
    """GET: show the user's API token (if any). POST: generate or regenerate it.

    Regenerating deletes the old token, so anything still using it stops working.
    """
    if request.method == "POST":
        had_token = Token.objects.filter(user=request.user).delete()[0] > 0
        Token.objects.create(user=request.user)
        messages.success(
            request,
            "Generated a new API token. The old one no longer works."
            if had_token
            else "Generated your API token.",
        )
        return redirect("accounts:me")
    token = Token.objects.filter(user=request.user).first()
    return render(request, "accounts/me.html", {"token": token})
