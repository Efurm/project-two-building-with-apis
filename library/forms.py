from django import forms

from .models import Entry

RATING_CHOICES = [(n, f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)]


class EntryForm(forms.ModelForm):
    """Edit a user's own data on an entry. Cross-field rules live on `Entry.clean()`.

    The rating, date watched, and times watched inputs are disabled in the browser
    unless status is Watched, so they may be missing from a POST; missing means empty.
    """

    rating = forms.TypedChoiceField(
        choices=[("", "Unrated"), *RATING_CHOICES],
        coerce=int,
        empty_value=None,
        required=False,
        widget=forms.RadioSelect,
    )
    times_watched = forms.IntegerField(min_value=0, required=False)

    class Meta:
        model = Entry
        fields = ["status", "rating", "date_watched", "times_watched", "notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "select w-full"}),
            "date_watched": forms.DateInput(attrs={"type": "date", "class": "input w-full"}),
            "notes": forms.Textarea(attrs={"rows": 5, "class": "textarea w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["times_watched"].widget.attrs.update({"class": "input w-full", "min": 0})
        watched = (self["status"].value() or "") == Entry.Status.WATCHED
        for name in ("rating", "date_watched", "times_watched"):
            self.fields[name].widget.attrs["data-watched-only"] = ""
            if not watched:
                # HTML-only disabling (not Field.disabled): the posted data stays the truth.
                self.fields[name].widget.attrs["disabled"] = True

    def clean_times_watched(self):
        return self.cleaned_data.get("times_watched") or 0


class EntryStatusForm(forms.ModelForm):
    """The one-click status control on a library card."""

    class Meta:
        model = Entry
        fields = ["status"]
