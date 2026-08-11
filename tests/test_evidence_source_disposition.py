from __future__ import annotations

import pytest

from src.evidence_requests.evidence_source_disposition import (
    EvidenceSourceDisposition,
    EvidenceSourceDispositionCatalog,
    EvidenceSourceDispositionError,
    EvidenceSourceDispositionKind,
    default_evidence_source_disposition_catalog,
)


def test_reference_material_is_classified_exactly() -> None:
    disposition = default_evidence_source_disposition_catalog().resolve(
        " codes of federal regulations "
    )

    assert disposition is not None
    assert disposition.kind == EvidenceSourceDispositionKind.AUTHORITATIVE_REFERENCE


def test_relevant_regulatory_reference_is_classified_exactly() -> None:
    disposition = default_evidence_source_disposition_catalog().resolve(
        "Relevant Codes of Federal Regulations"
    )

    assert disposition is not None
    assert disposition.kind == EvidenceSourceDispositionKind.AUTHORITATIVE_REFERENCE


def test_owner_exclusion_is_distinct_from_reference_material() -> None:
    disposition = default_evidence_source_disposition_catalog().resolve(
        "Collaborative Computing Procedures"
    )

    assert disposition is not None
    assert disposition.kind == EvidenceSourceDispositionKind.COLLECTION_EXCLUDED


def test_open_ended_collection_instruction_is_explicitly_excluded() -> None:
    disposition = default_evidence_source_disposition_catalog().resolve(
        "Other Relevant Documents or Records"
    )

    assert disposition is not None
    assert disposition.kind == EvidenceSourceDispositionKind.COLLECTION_EXCLUDED


def test_unknown_title_has_no_disposition() -> None:
    assert default_evidence_source_disposition_catalog().resolve("Unknown") is None


def test_disposition_requires_rationale() -> None:
    with pytest.raises(EvidenceSourceDispositionError, match="rationale"):
        EvidenceSourceDisposition(
            "Title",
            EvidenceSourceDispositionKind.COLLECTION_EXCLUDED,
            "",
        )


def test_catalog_rejects_duplicate_titles() -> None:
    dispositions = (
        EvidenceSourceDisposition(
            "Title",
            EvidenceSourceDispositionKind.COLLECTION_EXCLUDED,
            "First",
        ),
        EvidenceSourceDisposition(
            " title ",
            EvidenceSourceDispositionKind.AUTHORITATIVE_REFERENCE,
            "Second",
        ),
    )

    with pytest.raises(EvidenceSourceDispositionError, match="Duplicate"):
        EvidenceSourceDispositionCatalog(dispositions)
