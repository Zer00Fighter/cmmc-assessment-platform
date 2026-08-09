from __future__ import annotations

import pytest

from src.evidence_requests.evidence_object import (
    EvidenceArtifactType,
    EvidenceCategory,
    EvidenceObject,
)
from src.evidence_requests.evidence_object_catalog import (
    EvidenceObjectCatalog,
    EvidenceObjectCatalogError,
)


def make_evidence(
    evidence_id: str,
    canonical_name: str,
    *,
    aliases: tuple[str, ...] = (),
    category: EvidenceCategory = EvidenceCategory.OTHER,
    artifact_type: EvidenceArtifactType = EvidenceArtifactType.OTHER,
) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        canonical_name=canonical_name,
        aliases=aliases,
        category=category,
        artifact_type=artifact_type,
    )


def test_empty_catalog_constructs() -> None:
    catalog = EvidenceObjectCatalog()

    assert catalog.count == 0
    assert len(catalog) == 0
    assert catalog.objects == ()


def test_catalog_constructs_from_objects() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
            ),
            make_evidence(
                "EVIDENCE_RISK_ASSESSMENT",
                "Risk Assessment",
            ),
        )
    )

    assert catalog.count == 2


def test_iteration_is_deterministic_by_canonical_name() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_Z",
                "Z Evidence",
            ),
            make_evidence(
                "EVIDENCE_A",
                "A Evidence",
            ),
            make_evidence(
                "EVIDENCE_M",
                "M Evidence",
            ),
        )
    )

    assert [
        item.canonical_name
        for item in catalog
    ] == [
        "A Evidence",
        "M Evidence",
        "Z Evidence",
    ]


def test_get_by_id() -> None:
    evidence = make_evidence(
        "EVIDENCE_SSP",
        "System Security Plan",
    )

    catalog = EvidenceObjectCatalog((evidence,))

    assert catalog.get_by_id(
        "EVIDENCE_SSP"
    ) is evidence


def test_get_by_id_is_case_insensitive_and_trimmed() -> None:
    evidence = make_evidence(
        "EVIDENCE_SSP",
        "System Security Plan",
    )

    catalog = EvidenceObjectCatalog((evidence,))

    assert catalog.get_by_id(
        "  evidence_ssp  "
    ) is evidence


def test_get_by_canonical_name() -> None:
    evidence = make_evidence(
        "EVIDENCE_SSP",
        "System Security Plan",
    )

    catalog = EvidenceObjectCatalog((evidence,))

    assert catalog.get_by_name(
        "System Security Plan"
    ) is evidence


def test_get_by_alias() -> None:
    evidence = make_evidence(
        "EVIDENCE_SSP",
        "System Security Plan",
        aliases=(
            "SSP",
            "Security Plan",
        ),
    )

    catalog = EvidenceObjectCatalog((evidence,))

    assert catalog.get_by_name("SSP") is evidence
    assert catalog.get_by_name(
        "security plan"
    ) is evidence


def test_find_by_name_returns_none_for_unknown_name() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
            ),
        )
    )

    assert catalog.find_by_name(
        "Firewall Configuration"
    ) is None


def test_for_category_filters_objects() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_POLICY",
                "Access Control Policy",
                category=EvidenceCategory.POLICY,
            ),
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
                category=EvidenceCategory.PLAN,
            ),
            make_evidence(
                "EVIDENCE_IR_PLAN",
                "Incident Response Plan",
                category=EvidenceCategory.PLAN,
            ),
        )
    )

    result = catalog.for_category(
        EvidenceCategory.PLAN
    )

    assert [
        item.canonical_name
        for item in result
    ] == [
        "Incident Response Plan",
        "System Security Plan",
    ]


def test_contains_id() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
            ),
        )
    )

    assert catalog.contains_id("evidence_ssp")
    assert not catalog.contains_id(
        "EVIDENCE_UNKNOWN"
    )


def test_contains_name_matches_aliases() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
                aliases=("SSP",),
            ),
        )
    )

    assert catalog.contains_name(
        "System Security Plan"
    )
    assert catalog.contains_name("ssp")
    assert not catalog.contains_name("Unknown")


def test_duplicate_evidence_id_rejected() -> None:
    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Duplicate Evidence Object ID",
    ):
        EvidenceObjectCatalog(
            (
                make_evidence(
                    "EVIDENCE_SSP",
                    "System Security Plan",
                ),
                make_evidence(
                    "evidence_ssp",
                    "Different Object",
                ),
            )
        )


def test_duplicate_canonical_name_rejected() -> None:
    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Duplicate or ambiguous Evidence Object name",
    ):
        EvidenceObjectCatalog(
            (
                make_evidence(
                    "EVIDENCE_ONE",
                    "System Security Plan",
                ),
                make_evidence(
                    "EVIDENCE_TWO",
                    "system security plan",
                ),
            )
        )


def test_alias_collision_with_canonical_name_rejected() -> None:
    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Duplicate or ambiguous Evidence Object name",
    ):
        EvidenceObjectCatalog(
            (
                make_evidence(
                    "EVIDENCE_ONE",
                    "System Security Plan",
                    aliases=("SSP",),
                ),
                make_evidence(
                    "EVIDENCE_TWO",
                    "SSP",
                ),
            )
        )


def test_alias_collision_between_objects_rejected() -> None:
    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Duplicate or ambiguous Evidence Object name",
    ):
        EvidenceObjectCatalog(
            (
                make_evidence(
                    "EVIDENCE_ONE",
                    "System Security Plan",
                    aliases=("Security Plan",),
                ),
                make_evidence(
                    "EVIDENCE_TWO",
                    "Information Security Plan",
                    aliases=("security plan",),
                ),
            )
        )


def test_unknown_id_raises() -> None:
    catalog = EvidenceObjectCatalog()

    with pytest.raises(
        EvidenceObjectCatalogError,
        match="not found by ID",
    ):
        catalog.get_by_id(
            "EVIDENCE_UNKNOWN"
        )


def test_unknown_name_raises() -> None:
    catalog = EvidenceObjectCatalog()

    with pytest.raises(
        EvidenceObjectCatalogError,
        match="not found by name",
    ):
        catalog.get_by_name(
            "Unknown Evidence"
        )


def test_blank_id_lookup_rejected() -> None:
    catalog = EvidenceObjectCatalog()

    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Evidence ID cannot be blank",
    ):
        catalog.get_by_id("   ")


def test_blank_name_lookup_rejected() -> None:
    catalog = EvidenceObjectCatalog()

    with pytest.raises(
        EvidenceObjectCatalogError,
        match="Evidence name cannot be blank",
    ):
        catalog.get_by_name("   ")


def test_statistics() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_SSP",
                "System Security Plan",
                aliases=(
                    "SSP",
                    "Security Plan",
                ),
                category=EvidenceCategory.PLAN,
            ),
            make_evidence(
                "EVIDENCE_RISK",
                "Risk Assessment",
                aliases=(
                    "Risk Assessment Report",
                ),
                category=(
                    EvidenceCategory.ASSESSMENT
                ),
            ),
        )
    )

    statistics = catalog.statistics

    assert statistics.object_count == 2
    assert statistics.category_count == 2
    assert statistics.alias_count == 3


def test_catalog_is_framework_independent() -> None:
    catalog = EvidenceObjectCatalog(
        (
            make_evidence(
                "EVIDENCE_FIREWALL_CONFIGURATION",
                "Firewall Configuration",
                category=(
                    EvidenceCategory.CONFIGURATION
                ),
            ),
        )
    )

    evidence = catalog.get_by_id(
        "EVIDENCE_FIREWALL_CONFIGURATION"
    )

    assert not hasattr(evidence, "framework_id")
    assert not hasattr(evidence, "control_id")
    assert not hasattr(catalog, "framework_id")