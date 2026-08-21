from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Preview or remove local Omni backups older than the approved retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days", type=int,
            default=settings.OMNI_BACKUP_RETENTION_DAYS,
        )
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        days = options["retention_days"]
        if days < 1:
            raise CommandError("Retention must be at least one day.")
        root = Path(settings.OMNI_BACKUP_DIR).resolve()
        cutoff = timezone.now().timestamp() - timedelta(days=days).total_seconds()
        expired = sorted(
            item for item in root.glob("omni-backup-*.zip")
            if item.is_file() and item.stat().st_mtime < cutoff
        ) if root.exists() else []
        if not options["confirm"]:
            for item in expired:
                self.stdout.write(f"Would remove {item.name} and its SHA-256 sidecar.")
            self.stdout.write(self.style.WARNING(
                f"Dry run: {len(expired)} backup(s) exceed {days}-day retention. "
                "Run again with --confirm to remove them."
            ))
            return
        for item in expired:
            sidecar = item.with_suffix(".zip.sha256")
            item.unlink()
            sidecar.unlink(missing_ok=True)
        self.stdout.write(self.style.SUCCESS(
            f"Removed {len(expired)} backup(s) exceeding {days}-day retention."
        ))
