"""Refresh stale cached TMDB data.

TMDB's terms require cached data to be refreshed at least every 6 months, hence the
180-day default. Run with:  uv run --env-file .env python manage.py refresh_movies
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalog import services, tmdb
from catalog.models import Movie


class Command(BaseCommand):
    help = "Refresh stored movies whose TMDB data is older than N days (default 180)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than",
            type=int,
            default=180,
            metavar="DAYS",
            help="Refresh movies last fetched more than this many days ago (default: 180).",
        )

    def handle(self, *args, **options):
        days = options["older_than"]
        if days < 0:
            raise CommandError("--older-than must be 0 or more days.")

        cutoff = timezone.now() - datetime.timedelta(days=days)
        stale = Movie.objects.filter(last_fetched_at__lt=cutoff).order_by("last_fetched_at")
        total = stale.count()
        self.stdout.write(f"{total} movie(s) last fetched more than {days} day(s) ago.")

        refreshed = failed = 0
        for movie in stale:
            try:
                services.refresh_movie(movie)
            except tmdb.TMDBError as error:
                failed += 1
                self.stderr.write(f"  Failed: {movie.title} (TMDB id {movie.tmdb_id}): {error}")
            else:
                refreshed += 1
                self.stdout.write(f"  Refreshed: {movie.title} (TMDB id {movie.tmdb_id})")

        summary = f"Done: {refreshed} refreshed, {failed} failed."
        self.stdout.write(
            self.style.SUCCESS(summary) if not failed else self.style.WARNING(summary)
        )
