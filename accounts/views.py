from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


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
