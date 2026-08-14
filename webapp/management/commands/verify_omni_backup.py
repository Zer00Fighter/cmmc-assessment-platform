import hashlib
import json
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify an Omni backup checksum, archive integrity, manifest, and database payload."

    def add_arguments(self, parser):
        parser.add_argument("archive")

    def handle(self, *args, **options):
        archive = Path(options["archive"]).resolve()
        sidecar = archive.with_suffix(".zip.sha256")
        if not archive.is_file() or not sidecar.is_file():
            raise CommandError("Backup archive or SHA-256 sidecar is missing.")
        expected = sidecar.read_text(encoding="ascii").split()[0]
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != expected:
            raise CommandError("Backup checksum does not match.")
        with zipfile.ZipFile(archive) as source:
            if source.testzip():
                raise CommandError("Backup contains a corrupt member.")
            names = set(source.namelist())
            if not {"manifest.json", "database/omni.sqlite3"}.issubset(names):
                raise CommandError("Backup is missing required payloads.")
            json.loads(source.read("manifest.json"))
        self.stdout.write(self.style.SUCCESS("Backup verification passed."))
