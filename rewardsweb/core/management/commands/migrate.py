"""Custom Django management command for database migration.

https://stackoverflow.com/a/78460367
"""

from django.core.management.commands.migrate import Command as MigrateCommand


class Command(MigrateCommand):
    def sync_apps(self, connection, app_labels):
        """Enable custom extensions prior to table creation

        info:
            We use `MIGRATE: False` for faster test db creation,
            but this causes the migrations that enable extensions
            to not run. Manually enable them here.
        """
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        return super().sync_apps(connection, app_labels)