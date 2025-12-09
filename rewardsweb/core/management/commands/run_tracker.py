"""Django management command for running social media mention trackers."""

from django.core.management.base import BaseCommand

from trackers import runners


class Command(BaseCommand):
    help = "Run social media mention tracker process."

    def add_arguments(self, parser):
        """Add provider argument to command."""
        parser.add_argument("provider", type=str, nargs="?")

    def handle(self, *args, **options):
        """Run social media mention tracker process for `provider`.

        :var provider: social media provider name
        :type provider: str
        """
        provider = options.get("provider")
        if not provider or not hasattr(runners, f"run_{provider}_tracker"):
            self.stdout.write("Invalid provider name: %s" % (provider,))
            return None

        getattr(runners, f"run_{provider}_tracker")()
        self.stdout.write(f"{provider.capitalize()} tracker exited")
