import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.backup import sha256_file


class Command(BaseCommand):
    help = "Create a local Omni database and private-evidence backup archive."

    def handle(self, *args, **options):
        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Local backup currently supports SQLite. Use pg_dump for PostgreSQL.")
        destination = Path(settings.OMNI_BACKUP_DIR).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%dT%H%M%S%fZ")
        archive = destination / f"omni-backup-{stamp}.zip"
        source_db = Path(settings.DATABASES["default"]["NAME"]).resolve()
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "omni.sqlite3"
            source = sqlite3.connect(source_db)
            target = sqlite3.connect(snapshot)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            manifest = {
                "schema_version": 2,
                "created_at": timezone.now().isoformat(),
                "database_engine": "sqlite3",
                "database": "database/omni.sqlite3",
                "evidence_root": "private_uploads/",
                "files": [],
            }
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                output.write(snapshot, "database/omni.sqlite3")
                manifest["files"].append({
                    "path": "database/omni.sqlite3", "size_bytes": snapshot.stat().st_size,
                    "sha256": sha256_file(snapshot),
                })
                media_root = Path(settings.MEDIA_ROOT)
                if media_root.exists():
                    for item in sorted(media_root.rglob("*")):
                        if item.is_file():
                            member = (Path("private_uploads") / item.relative_to(media_root)).as_posix()
                            output.write(item, member)
                            manifest["files"].append({
                                "path": member, "size_bytes": item.stat().st_size,
                                "sha256": sha256_file(item),
                            })
                output.writestr("manifest.json", json.dumps(manifest, indent=2))
        digest = sha256_file(archive)
        archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
        self.stdout.write(self.style.SUCCESS(f"Created {archive.name} with SHA-256 sidecar."))
