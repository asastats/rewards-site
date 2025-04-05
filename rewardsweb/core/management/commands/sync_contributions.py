from django.core.management.base import BaseCommand
from django.utils import timezone
from core.services.contribution.sync import ContributionSyncService
from utils.seeder.seeder import SeederUtil
import os

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-url", type=str, required=True)

    def handle(self, *args, **options):
        sheet_url = options["sheet_url"]
        sync_service = ContributionSyncService()
        output_csv = sync_service.fetch_and_convert(sheet_url)

        if not output_csv:
            self.stdout.write(self.style.ERROR("Failed to fetch or convert the Google Sheet. Check the URL or logs for details."))
            return

        seeder = SeederUtil()
        new_contributions = seeder.seed_contributions(output_csv)

        if new_contributions == 0:
            self.stdout.write(self.style.SUCCESS(f"Database is up-to-date as of {timezone.now().strftime('%Y-%m-%d')}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Inserted {new_contributions} new contributions as of {timezone.now().strftime('%Y-%m-%d')}."))

        if os.path.exists(output_csv):
            os.remove(output_csv)