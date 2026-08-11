from __future__ import annotations

import pytest

from src.evidence.evidence_object import EvidenceObject
from src.evidence_requests.evidence_source_mapping import (
    DEFAULT_EVIDENCE_SOURCE_MAPPINGS,
    EvidenceSourceMapping,
    EvidenceSourceMappingCatalog,
    EvidenceSourceMappingError,
    default_evidence_source_mapping_catalog,
)


def test_default_catalog_resolves_compound_source_title_exactly() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Security Plan System Design Documentation"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0001", "EV-0033")


def test_mapping_lookup_is_case_insensitive_and_trimmed() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "  patch and vulnerability management records  "
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0077", "EV-0078")


def test_batch_1_compound_mapping_preserves_independent_artifacts() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Analysis Tools and Associated Outputs"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0105", "EV-0106")


def test_batch_5_inventory_review_mapping_preserves_procedure_and_inventories() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Inventory Review and Update Records"
    )

    assert tuple(item.evidence_id for item in resolved) == (
        "EV-0139",
        "EV-0021",
        "EV-0022",
        "EV-0023",
    )


def test_batch_6_information_at_rest_maps_to_information_asset_inventory() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "List of Information at Rest Requiring Confidentiality Protections"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0023",)


def test_batch_6_internal_boundaries_preserve_diagram_and_architecture() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "List of Key Internal Boundaries of the System"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0031", "EV-0033")


def test_batch_7_public_publishers_map_to_public_communications_procedures() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "List of Users Authorized to Post Publicly Accessible Content on Organizational Systems"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0141",)


def test_batch_8_personnel_lifecycle_maps_to_human_resources_manual() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Personnel Transfer and Termination Procedures"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0144",)


def test_batch_9_information_at_rest_preserves_crypto_and_media_procedures() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Protection of Information at Rest Procedures"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0119", "EV-0092")


def test_batch_9_public_information_response_preserves_incident_and_comms() -> None:
    resolved = default_evidence_source_mapping_catalog().resolve(
        "Records of Response to Nonpublic Information on Public Websites"
    )

    assert tuple(item.evidence_id for item in resolved) == ("EV-0043", "EV-0141")


def test_unknown_source_title_returns_no_mapping() -> None:
    assert default_evidence_source_mapping_catalog().resolve("Unknown") == ()


def test_default_mapping_titles_are_unique() -> None:
    titles = [item.source_title.casefold() for item in DEFAULT_EVIDENCE_SOURCE_MAPPINGS]

    assert len(titles) == len(set(titles))


def test_catalog_rejects_unknown_evidence_id() -> None:
    with pytest.raises(EvidenceSourceMappingError, match="Unknown Evidence Object IDs"):
        EvidenceSourceMappingCatalog(
            (EvidenceSourceMapping("Source", ("EV-9999",)),),
            evidence_objects=(EvidenceObject("EV-0001", "Known"),),
        )


def test_catalog_rejects_duplicate_source_title() -> None:
    mappings = (
        EvidenceSourceMapping("Source", ("EV-0001",)),
        EvidenceSourceMapping(" source ", ("EV-0001",)),
    )

    with pytest.raises(EvidenceSourceMappingError, match="Duplicate source"):
        EvidenceSourceMappingCatalog(
            mappings,
            evidence_objects=(EvidenceObject("EV-0001", "Known"),),
        )
