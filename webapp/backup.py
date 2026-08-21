from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


class BackupValidationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_zip_member(source: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with source.open(name) as member:
        for chunk in iter(lambda: member.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member_name(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def sqlite_integrity(path: Path) -> None:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise BackupValidationError(f"Backup database cannot be opened: {exc}") from exc
    if not result or result[0] != "ok":
        raise BackupValidationError("Backup database failed SQLite integrity_check.")


def verify_backup(archive: Path) -> dict:
    archive = archive.resolve()
    sidecar = archive.with_suffix(".zip.sha256")
    if not archive.is_file() or not sidecar.is_file():
        raise BackupValidationError("Backup archive or SHA-256 sidecar is missing.")
    try:
        expected = sidecar.read_text(encoding="ascii").split()[0]
    except (IndexError, UnicodeError) as exc:
        raise BackupValidationError("Backup SHA-256 sidecar is invalid.") from exc
    if len(expected) != 64 or sha256_file(archive) != expected:
        raise BackupValidationError("Backup checksum does not match.")
    try:
        with zipfile.ZipFile(archive) as source:
            corrupt = source.testzip()
            if corrupt:
                raise BackupValidationError(f"Backup contains a corrupt member: {corrupt}")
            names = source.namelist()
            if any(not safe_member_name(name) for name in names):
                raise BackupValidationError("Backup contains an unsafe member path.")
            if len(names) != len(set(names)):
                raise BackupValidationError("Backup contains duplicate member paths.")
            required = {"manifest.json", "database/omni.sqlite3"}
            if not required.issubset(names):
                raise BackupValidationError("Backup is missing required payloads.")
            try:
                manifest = json.loads(source.read("manifest.json"))
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise BackupValidationError("Backup manifest is invalid.") from exc
            if manifest.get("schema_version", 1) >= 2:
                entries = {item["path"]: item for item in manifest.get("files", [])}
                payload_names = set(names) - {"manifest.json"}
                if set(entries) != payload_names:
                    raise BackupValidationError("Backup manifest does not match archive payloads.")
                for name, item in entries.items():
                    info = source.getinfo(name)
                    if info.file_size != item.get("size_bytes"):
                        raise BackupValidationError(f"Backup size mismatch: {name}")
                    if sha256_zip_member(source, name) != item.get("sha256"):
                        raise BackupValidationError(f"Backup payload checksum mismatch: {name}")
            with tempfile.TemporaryDirectory() as temporary:
                database = Path(temporary) / "omni.sqlite3"
                with source.open("database/omni.sqlite3") as payload, database.open("wb") as target:
                    for chunk in iter(lambda: payload.read(1024 * 1024), b""):
                        target.write(chunk)
                sqlite_integrity(database)
    except zipfile.BadZipFile as exc:
        raise BackupValidationError("Backup archive is not a valid ZIP file.") from exc
    return manifest
