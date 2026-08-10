from __future__ import annotations

import pytest

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject
from src.evidence.evidence_resolver import (
    EvidenceResolutionStatus,
    EvidenceResolver,
    EvidenceResolverError,
)


def test_knowledge_contains_approved_first_forty_objects() -> None:
    assert len(EVIDENCE_KNOWLEDGE) == 40
    assert EVIDENCE_KNOWLEDGE[0].evidence_id == "EV-0001"
    assert EVIDENCE_KNOWLEDGE[-1].evidence_id == "EV-0040"


def test_resolves_canonical_name_exactly() -> None:
    result = EvidenceResolver().resolve("Credential Policy")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0016"
    assert result.evidence.canonical_name == "Credential Policy"


def test_resolves_alias_exactly() -> None:
    result = EvidenceResolver().resolve("Password Policy")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0016"
    assert result.matched_name == "Password Policy"


def test_resolution_is_case_insensitive_and_trimmed() -> None:
    result = EvidenceResolver().resolve("  system security plan  ")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0001"


def test_punctuation_variation_is_not_resolved() -> None:
    result = EvidenceResolver().resolve("Access-Control Policy & Procedures")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert result.evidence_id is None


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
    results = EvidenceResolver().resolve_many(("POA&M", "Unknown", "User Account List"))

    assert [result.evidence_id for result in results] == [
        "EV-0007",
        None,
        "EV-0011",
    ]


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("List of System Accounts", "EV-0011"),
        ("Privileged Account List", "EV-0012"),
        ("Access Approval Records", "EV-0013"),
        ("Access Recertification Records", "EV-0014"),
        ("Password Policy", "EV-0016"),
        ("MFA Configuration", "EV-0018"),
        ("VPN Configuration", "EV-0019"),
        ("IdP Configuration", "EV-0020"),
    ),
)
def test_cross_framework_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Device Inventory", "EV-0021"),
        ("Application Inventory", "EV-0022"),
        ("Data Inventory", "EV-0023"),
        ("Hardening Standard", "EV-0027"),
        ("Change Tickets", "EV-0029"),
        ("Network Topology Diagram", "EV-0031"),
        ("System Design Documentation", "EV-0033"),
        ("Firewall Rules", "EV-0035"),
        ("System Logs", "EV-0036"),
        ("SIEM Configuration", "EV-0039"),
        ("SIEM Alerts", "EV-0040"),
    ),
)
def test_sprint_3_5_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


def test_ambiguous_names_are_rejected() -> None:
    first = EvidenceObject(
        evidence_id="EV-A",
        canonical_name="First Policy",
        aliases=("Shared Name",),
    )
    second = EvidenceObject(
        evidence_id="EV-B",
        canonical_name="Second Policy",
        aliases=("shared name",),
    )

    with pytest.raises(
        EvidenceResolverError,
        match="Ambiguous Evidence Object name",
    ):
        EvidenceResolver((first, second))
