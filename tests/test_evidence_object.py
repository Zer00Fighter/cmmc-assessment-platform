from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.evidence_requests.evidence_object import (
    EvidenceArtifactType,
    EvidenceCategory,
    EvidenceObject,
    EvidenceObjectError,
)


def test_evidence_object_constructs() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SYSTEM_SECURITY_PLAN",
        canonical_name="System Security Plan",
        aliases=(
            "SSP",
            "Security Plan",
        ),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description=(
            "Primary system security planning document."
        ),
    )

    assert (
        evidence.evidence_id
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )

    assert (
        evidence.canonical_name
        == "System Security Plan"
    )

    assert evidence.aliases == (
        "SSP",
        "Security Plan",
    )

    assert evidence.category == EvidenceCategory.PLAN

    assert (
        evidence.artifact_type
        == EvidenceArtifactType.DOCUMENT
    )

    assert evidence.description == (
        "Primary system security planning document."
    )


def test_values_are_trimmed() -> None:
    evidence = EvidenceObject(
        evidence_id="  EVIDENCE_SSP  ",
        canonical_name="  System Security Plan  ",
        aliases=(
            "  SSP  ",
            "  Security Plan  ",
        ),
        description="  Description text.  ",
    )

    assert evidence.evidence_id == "EVIDENCE_SSP"
    assert evidence.canonical_name == "System Security Plan"

    assert evidence.aliases == (
        "SSP",
        "Security Plan",
    )

    assert evidence.description == "Description text."


def test_blank_evidence_id_rejected() -> None:
    with pytest.raises(
        EvidenceObjectError,
        match="evidence_id",
    ):
        EvidenceObject(
            evidence_id="   ",
            canonical_name="System Security Plan",
        )


def test_blank_canonical_name_rejected() -> None:
    with pytest.raises(
        EvidenceObjectError,
        match="canonical_name",
    ):
        EvidenceObject(
            evidence_id="EVIDENCE_SSP",
            canonical_name="   ",
        )


def test_blank_aliases_are_removed() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=(
            "",
            "   ",
            "SSP",
        ),
    )

    assert evidence.aliases == (
        "SSP",
    )


def test_duplicate_aliases_are_removed_case_insensitively() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=(
            "SSP",
            "ssp",
            "Security Plan",
            "SECURITY PLAN",
        ),
    )

    assert evidence.aliases == (
        "SSP",
        "Security Plan",
    )


def test_canonical_name_is_not_repeated_as_alias() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=(
            "System Security Plan",
            "system security plan",
            "SSP",
        ),
    )

    assert evidence.aliases == (
        "SSP",
    )


def test_names_contains_canonical_name_first() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=(
            "SSP",
            "Security Plan",
        ),
    )

    assert evidence.names == (
        "System Security Plan",
        "SSP",
        "Security Plan",
    )


def test_key_is_case_insensitive_identity() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_System_Security_Plan",
        canonical_name="System Security Plan",
    )

    assert evidence.key == (
        "evidence_system_security_plan"
    )


def test_matches_canonical_name() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=("SSP",),
    )

    assert evidence.matches_name(
        "System Security Plan"
    )

    assert evidence.matches_name(
        "system security plan"
    )

    assert evidence.matches_name(
        "  SYSTEM SECURITY PLAN  "
    )


def test_matches_alias() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=(
            "SSP",
            "Security Plan",
        ),
    )

    assert evidence.matches_name("SSP")

    assert evidence.matches_name(
        "security plan"
    )


def test_does_not_match_unknown_name() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=("SSP",),
    )

    assert not evidence.matches_name(
        "Firewall Configuration"
    )


def test_blank_name_does_not_match() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
    )

    assert not evidence.matches_name("")
    assert not evidence.matches_name("   ")


def test_object_is_immutable() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        evidence.canonical_name = "Changed"


def test_objects_with_same_values_are_equal() -> None:
    first = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=("SSP",),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
    )

    second = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=("SSP",),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
    )

    assert first == second


def test_object_is_hashable() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_SSP",
        canonical_name="System Security Plan",
        aliases=("SSP",),
    )

    values = {
        evidence,
    }

    assert evidence in values


def test_category_enum_values() -> None:
    assert EvidenceCategory.POLICY.value == "Policy"
    assert EvidenceCategory.PROCEDURE.value == "Procedure"
    assert EvidenceCategory.PLAN.value == "Plan"
    assert EvidenceCategory.CONFIGURATION.value == "Configuration"
    assert EvidenceCategory.INVENTORY.value == "Inventory"
    assert EvidenceCategory.LOG.value == "Log"
    assert EvidenceCategory.ASSESSMENT.value == "Assessment"
    assert EvidenceCategory.POAM.value == "POA&M"


def test_artifact_type_enum_values() -> None:
    assert (
        EvidenceArtifactType.DOCUMENT.value
        == "Document"
    )

    assert (
        EvidenceArtifactType.DATASET.value
        == "Dataset"
    )

    assert (
        EvidenceArtifactType.CONFIGURATION.value
        == "Configuration"
    )

    assert (
        EvidenceArtifactType.DATABASE_EXPORT.value
        == "Database Export"
    )


def test_framework_independent_object() -> None:
    evidence = EvidenceObject(
        evidence_id="EVIDENCE_FIREWALL_CONFIGURATION",
        canonical_name="Firewall Configuration",
        aliases=(
            "Firewall Config",
            "Running Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=(
            EvidenceArtifactType.CONFIGURATION
        ),
    )

    assert not hasattr(
        evidence,
        "framework_id",
    )

    assert not hasattr(
        evidence,
        "control_id",
    )

    assert not hasattr(
        evidence,
        "owner",
    )