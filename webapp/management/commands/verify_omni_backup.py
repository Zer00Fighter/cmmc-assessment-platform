from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from webapp.backup import BackupValidationError, verify_backup


class Command(BaseCommand):
    help = "Verify an Omni backup checksum, archive integrity, manifest, and database payload."

    def add_arguments(self, parser):
        parser.add_argument("archive")

    def handle(self, *args, **options):
        archive = Path(options["archive"]).resolve()
        try:
            manifest = verify_backup(archive)
        except BackupValidationError as exc:
            raise CommandError(str(exc)) from exc
        count = len(manifest.get("files", []))
        self.stdout.write(self.style.SUCCESS(
            f"Backup verification passed ({count} authenticated payloads)."
        ))
