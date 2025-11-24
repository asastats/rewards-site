"""Django management command for importing and mapping existing data to database."""

import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from utils.helpers import convert_and_clean_excel
from utils.importers import import_from_csv
from utils.mappers import map_github_issues


class Command(BaseCommand):
    help = "Calls script which converts Excel file to CSV."

    def add_arguments(self, parser):
        """Add optional input_file, output files and token arguments to command."""
        parser.add_argument("token", type=str, nargs="?", default="")
        parser.add_argument("input", type=str, nargs="?", default="")
        parser.add_argument("output", type=str, nargs="?", default="")
        parser.add_argument("legacy", type=str, nargs="?", default="")

    def handle(self, *args, **options):
        """Call `convert_and_clean_excel` script to export Excel file to CSV."""

        fixtures_dir = settings.BASE_DIR.parent / "fixtures"

        issue_tracker_api_token = options.get("token")
        input_file = (
            Path(options.get("input"))
            if options.get("input")
            else fixtures_dir / "contributions.xlsx"
        )
        output_file = (
            Path(options.get("output"))
            if options.get("output")
            else fixtures_dir / "contributions.csv"
        )
        legacy_file = (
            Path(options.get("legacy"))
            if options.get("legacy")
            else fixtures_dir / "legacy_contributions.csv"
        )

        a = time.time()
        convert_and_clean_excel(input_file, output_file, legacy_file)
        self.stdout.write(
            "CSV successfully exported into %s file!" % (output_file.name)
        )

        response = import_from_csv(output_file, legacy_file)
        if not response:
            self.stdout.write("Records successfully imported!")
            response = map_github_issues(
                issue_tracker_api_token=issue_tracker_api_token
            )
            if not response:
                self.stdout.write("Issues successfully mapped!")

            else:
                self.stdout.write(response)

        else:
            self.stdout.write(response)

        print(time.time() - a)
