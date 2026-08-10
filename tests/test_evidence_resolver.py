from __future__ import annotations

import pytest

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject
from src.evidence.evidence_resolver import (
    EvidenceResolutionStatus,
    EvidenceResolver,
    EvidenceResolverError,
)


def test_knowledge_contains_three_complete_chunks() -> None:
    assert len(EVIDENCE_KNOWLEDGE) == 30
    assert EVIDENCE_KNOWLEDGE[0].evidence_id == "EV-0001"
    assert EVIDENCE_KNOWLEDGE[-1].evidence_id == "EV-0030"


def test_resolves_canonical_name_exactly() -> None:
    result = EvidenceResolver().resolve("Audit Logs")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0021"
    assert result.evidence.canonical_name == "Audit Logs"


def test_resolves_alias_exactly() -> None:
    result = EvidenceResolver().resolve("System Logs")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0021"
    assert result.matched_name == "System Logs"


def test_resolution_is_case_insensitive_and_trimmed() -> None:
    result = EvidenceResolver().resolve("  system security plan  ")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0001"


def test_normalized_resolution_handles_punctuation() -> None:
    result = EvidenceResolver().resolve("Access-Control Policy & Procedures")

    assert result.status == EvidenceResolutionStatus.NORMALIZED
    assert result.evidence_id == "EV-0011"


def test_unknown_name_is_unresolved() -> None:
    result = EvidenceResolver().resolve("Quantum Security Ledger")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert not result.resolved
    assert result.evidence is None
    assert result.evidence_id is None


def test_blank_name_is_unresolved() -> None:
    result = EvidenceResolver().resolve("   ")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert result.source_name == ""


def test_resolve_many_preserves_input_order() -> None:
    results = EvidenceResolver().resolve_many(
        ("Firewall Rules", "Unknown", "Asset Inventory")
    )

    assert [result.evidence_id for result in results] == [
        "EV-0020",
        None,
        "EV-0014",
    ]


def test_normalize_is_deterministic() -> None:
    assert (
        EvidenceResolver.normalize("  Policy & Procedures  ") == "policy and procedures"
    )


def test_ambiguous_normalized_names_are_rejected() -> None:
    first = EvidenceObject(
        evidence_id="EV-A",
        canonical_name="Policy & Procedure",
    )
    second = EvidenceObject(
        evidence_id="EV-B",
        canonical_name="Policy and Procedure",
    )

    with pytest.raises(
        EvidenceResolverError,
        match="Ambiguous Evidence Object name",
    ):
        EvidenceResolver((first, second))
