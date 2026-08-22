from __future__ import annotations

import zipfile
from pathlib import PurePath

from django.core.exceptions import ValidationError

ZIP_EXTENSIONS = {"docx", "xlsx", "xlsm", "zip"}
TEXT_EXTENSIONS = {"csv", "txt", "json", "xml", "log"}


def validate_uploaded_file(
    upload, *, allowed_extensions: set[str], max_bytes: int
) -> None:
    name = PurePath(upload.name or "").name
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if not name or suffix not in allowed_extensions:
        raise ValidationError(
            "The uploaded file type is not allowed. Renaming a file does not change its type."
        )
    if upload.size > max_bytes:
        raise ValidationError(
            f"The uploaded file cannot exceed {max_bytes // (1024 * 1024)} MB."
        )
    if upload.size == 0:
        raise ValidationError("The uploaded file is empty.")
    position = upload.tell()
    try:
        upload.seek(0)
        header = upload.read(16)
        upload.seek(0)
        if suffix == "pdf" and not header.startswith(b"%PDF-"):
            raise ValidationError("The file content is not a valid PDF signature.")
        if suffix == "png" and header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValidationError("The file content is not a valid PNG signature.")
        if suffix in {"jpg", "jpeg"} and not header.startswith(b"\xff\xd8\xff"):
            raise ValidationError("The file content is not a valid JPEG signature.")
        if suffix in {"doc", "xls"} and not header.startswith(
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        ):
            raise ValidationError(
                "The file content is not a valid legacy Office signature."
            )
        if suffix in ZIP_EXTENSIONS:
            if not header.startswith(b"PK"):
                raise ValidationError(
                    "The file content is not a valid ZIP-based document."
                )
            try:
                with zipfile.ZipFile(upload) as archive:
                    entries = archive.infolist()
                    if len(entries) > 5000:
                        raise ValidationError("The archive contains too many entries.")
                    total = sum(item.file_size for item in entries)
                    if total > 250 * 1024 * 1024:
                        raise ValidationError("The expanded archive is too large.")
                    if any(item.flag_bits & 0x1 for item in entries):
                        raise ValidationError(
                            "Encrypted ZIP entries are not accepted for evidence review."
                        )
            except zipfile.BadZipFile as exc:
                raise ValidationError("The ZIP-based file is corrupt.") from exc
        if suffix in TEXT_EXTENSIONS:
            sample = upload.read(min(upload.size, 64 * 1024))
            if b"\x00" in sample:
                raise ValidationError("Text-based uploads cannot contain null bytes.")
    finally:
        upload.seek(position)
