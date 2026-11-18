// Small progressive enhancements for the entry edit form.
// Rating, date watched, and times watched apply only when status is "Watched".
document.addEventListener("change", (event) => {
  const status = event.target.closest('form[data-entry-form] select[name="status"]');
  if (!status) return;
  const watched = status.value === "watched";
  status.form.querySelectorAll("[data-watched-only]").forEach((el) => {
    el.disabled = !watched;
  });
});

// "Clear" next to the star rating selects the hidden "Unrated" radio.
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear-rating]");
  if (!button) return;
  const unrated = button.form.querySelector('input[name="rating"][value=""]');
  if (unrated) unrated.checked = true;
});
