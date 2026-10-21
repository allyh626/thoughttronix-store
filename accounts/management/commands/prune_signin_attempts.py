"""Delete sign-in attempts older than 90 days, so the history doesn't grow
forever. Safe to run any time, as often as you like."""

from django.core.management.base import BaseCommand

from accounts.models import SignInAttempt


class Command(BaseCommand):
    help = "Delete sign-in attempts older than 90 days."

    def handle(self, *args, **options):
        deleted, _ = SignInAttempt.objects.stale().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} old sign-in attempts.")
        )
