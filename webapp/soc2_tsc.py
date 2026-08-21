"""Versioned AICPA TSC identifier baseline for Omni.

The bundled catalog intentionally contains identifiers, hierarchy, and
Omni-authored labels only. It does not reproduce AICPA criterion text or
Points of Focus.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Framework, Requirement

CATALOG_PATH = Path(settings.BASE_DIR) / "data" / "frameworks" / "aicpa_tsc_2017_2022.json"

EXPECTED_BY_DOMAIN = {
    "Security — Common Criteria": (
        *(f"CC1.{n}" for n in range(1, 6)),
        *(f"CC2.{n}" for n in range(1, 4)),
        *(f"CC3.{n}" for n in range(1, 5)),
        *(f"CC4.{n}" for n in range(1, 3)),
        *(f"CC5.{n}" for n in range(1, 4)),
        *(f"CC6.{n}" for n in range(1, 9)),
        *(f"CC7.{n}" for n in range(1, 6)),
        "CC8.1", "CC9.1", "CC9.2",
    ),
    "Availability": ("A1.1", "A1.2", "A1.3"),
    "Processing Integrity": tuple(f"PI1.{n}" for n in range(1, 6)),
    "Confidentiality": ("C1.1", "C1.2"),
    "Privacy": (
        "P1.1", "P2.1", "P3.1", "P3.2", "P4.1", "P4.2", "P4.3",
        "P5.1", "P5.2", *(f"P6.{n}" for n in range(1, 8)), "P7.1", "P8.1",
    ),
}


def load_catalog(path: Path = CATALOG_PATH) -> tuple[dict, str]:
    content = path.read_bytes()
    return json.loads(content.decode("utf-8")), hashlib.sha256(content).hexdigest()


def validate_catalog(catalog: dict) -> dict:
    errors: list[str] = []
    criteria = catalog.get("criteria", [])
    actual: dict[str, list[str]] = {}
    seen: set[str] = set()
    for row_number, row in enumerate(criteria, 1):
        if not isinstance(row, list) or len(row) != 3:
            errors.append(f"Criterion row {row_number} must contain identifier, domain, and label.")
            continue
        identifier, domain, label = (str(value).strip() for value in row)
        if identifier in seen:
            errors.append(f"Duplicate criterion identifier: {identifier}")
        seen.add(identifier)
        actual.setdefault(domain, []).append(identifier)
        if not label:
            errors.append(f"Criterion {identifier} has no descriptive label.")
    for domain, expected in EXPECTED_BY_DOMAIN.items():
        found = tuple(actual.get(domain, ()))
        missing = sorted(set(expected) - set(found))
        invented = sorted(set(found) - set(expected))
        if missing:
            errors.append(f"{domain} missing: {', '.join(missing)}")
        if invented:
            errors.append(f"{domain} unexpected: {', '.join(invented)}")
    unexpected_domains = sorted(set(actual) - set(EXPECTED_BY_DOMAIN))
    if unexpected_domains:
        errors.append(f"Unexpected domains: {', '.join(unexpected_domains)}")
    metadata = catalog.get("framework", {})
    if not str(metadata.get("source_url", "")).startswith("https://www.aicpa-cima.com/"):
        errors.append("The framework source must be an official AICPA/CIMA URL.")
    if not metadata.get("copyright_notice"):
        errors.append("A copyright notice is required.")
    return {
        "valid": not errors,
        "errors": errors,
        "criterion_count": len(criteria),
        "domain_counts": {domain: len(actual.get(domain, ())) for domain in EXPECTED_BY_DOMAIN},
    }


@transaction.atomic
def install_baseline(path: Path = CATALOG_PATH) -> tuple[Framework, bool, dict]:
    catalog, digest = load_catalog(path)
    report = validate_catalog(catalog)
    if not report["valid"]:
        raise ValueError("Invalid AICPA TSC baseline: " + "; ".join(report["errors"]))
    metadata = catalog["framework"]
    existing = Framework.objects.filter(code=metadata["code"]).first()
    if existing:
        identifiers = set(existing.requirements.values_list("requirement_id", flat=True))
        expected = {row[0] for row in catalog["criteria"]}
        if existing.source_sha256 != digest or identifiers != expected:
            raise ValueError("The existing TSC baseline differs from this immutable catalog version.")
        return existing, False, report
    framework = Framework.objects.create(
        code=metadata["code"], name=metadata["name"], version=metadata["version"],
        authority=metadata["authority"], description=(
            f"{metadata['content_scope']} Source: {metadata['source_url']} "
            f"{metadata['copyright_notice']}"
        ), source_filename=path.name, source_sha256=digest,
    )
    Requirement.objects.bulk_create([
        Requirement(
            framework=framework, requirement_id=identifier, domain=domain,
            title=label,
            statement=f"Omni descriptive summary: {label}. Consult the licensed AICPA publication for authoritative wording.",
            source_reference=metadata["source_url"], source_row=index,
        )
        for index, (identifier, domain, label) in enumerate(catalog["criteria"], 1)
    ])
    return framework, True, report
