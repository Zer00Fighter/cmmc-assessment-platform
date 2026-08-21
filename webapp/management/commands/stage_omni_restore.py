import json
import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from webapp.backup import BackupValidationError, sqlite_integrity, verify_backup


class Command(BaseCommand):
    help = "Verify and extract an Omni backup into an isolated recovery staging directory."

    def add_arguments(self, parser):
        parser.add_argument("archive")
        parser.add_argument("--destination")

    def handle(self, *args, **options):
        archive = Path(options["archive"]).resolve()
        destination = Path(options["destination"]).resolve() if options["destination"] else (
            Path(settings.OMNI_RESTORE_STAGING_DIR).resolve() / archive.stem
        )
        database = Path(settings.DATABASES["default"]["NAME"]).resolve()
        media = Path(settings.MEDIA_ROOT).resolve()
        if (destination in (database, media, database.parent)
                or media in destination.parents):
            raise CommandError("Recovery staging cannot overwrite an Omni runtime location.")
        if destination.exists() and any(destination.iterdir()):
            raise CommandError("Recovery staging destination must be absent or empty.")
        try:
            manifest = verify_backup(archive)
        except BackupValidationError as exc:
            raise CommandError(str(exc)) from exc
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            for info in source.infolist():
                target = destination / Path(info.filename)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(info) as payload, target.open("wb") as output:
                    shutil.copyfileobj(payload, output, length=1024 * 1024)
        sqlite_integrity(destination / "database" / "omni.sqlite3")
        report = {
            "source_archive": archive.name,
            "created_at": manifest.get("created_at"),
            "authenticated_payloads": len(manifest.get("files", [])),
            "database_integrity": "ok",
            "status": "STAGED_ONLY_DO_NOT_RUN_IN_PLACE",
        }
        (destination / "recovery-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        self.stdout.write(self.style.SUCCESS(
            f"Recovery staged and verified at {destination}. Runtime data was not changed."
        ))
