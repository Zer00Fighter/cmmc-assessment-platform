from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evidence_requests.request_catalog import (
    EvidenceRequestCatalog,
    EvidenceRequestCatalogError,
    EvidenceRequestCatalogNotFoundError,
    EvidenceRequestTemplate,
)
from src.evidence_requests.request_model import (
    ControlReference,
    EvidenceGuidance,
    EvidenceRequestCategory,
    EvidenceRequestPriority,
    EvidenceRequestType,
    ObjectiveReference,
)


def make_template(
    *,
    template_id: str = "ACCESS_CONTROL_POLICY",
    framework_id: str = "CMMC_L2",
    primary_control_id: str = "AC.L2-3.1.1",
    title: str = "Access Control Policy",
    reuse_key: str = "ACCESS_CONTROL_POLICY",
) -> EvidenceRequestTemplate:
    return EvidenceRequestTemplate(
        template_id=template_id,
        framework_id=framework_id,
        title=title,
        description=(
            "Provide the current approved access "
            "control policy and related evidence."
        ),
        category=(
            EvidenceRequestCategory.SYSTEM_DESIGN
        ),
        evidence_type=EvidenceRequestType.POLICY,
        primary_control=ControlReference(
            framework_id=framework_id,
            control_id=primary_control_id,
            control_title="Authorized Access Control",
        ),
        related_controls=(
            ControlReference(
                framework_id=framework_id,
                control_id="AC.L2-3.1.2",
            ),
            ControlReference(
                framework_id=framework_id,
                control_id="AC.L2-3.1.5",
            ),
        ),
        objectives=(
            ObjectiveReference(
                framework_id=framework_id,
                control_id=primary_control_id,
                objective_id="a",
                objective_text=(
                    "Authorized users are identified."
                ),
            ),
        ),
        guidance=(
            EvidenceGuidance(
                evidence_type=EvidenceRequestType.POLICY,
                description=(
                    "Provide the current approved "
                    "Access Control Policy."
                ),
                example_artifacts=(
                    "Access Control Policy",
                    "Identity and Access Management Policy",
                ),
            ),
        ),
        default_priority=(
            EvidenceRequestPriority.HIGH
        ),
        suggested_owner="Information Security",
        sprs_weight=5,
        reuse_key=reuse_key,
        tags=(
            "Access Control",
            "Governance",
            "Policy",
        ),
        source_reference="CMMC Assessment Guide",
    )


def make_mapping() -> dict:
    return {
        "schema_version": "1.0",
        "framework_id": "CMMC_L2",
        "templates": [
            {
                "template_id": "ACCESS_CONTROL_POLICY",
                "title": "Access Control Policy",
                "description": (
                    "Provide the current approved "
                    "Access Control Policy."
                ),
                "category": (
                    "System Design Documentation"
                ),
                "evidence_type": "Policy",
                "primary_control": {
                    "control_id": "AC.L2-3.1.1",
                    "control_title": (
                        "Authorized Access Control"
                    ),
                },
                "related_controls": [
                    {
                        "control_id": "AC.L2-3.1.2",
                    },
                    {
                        "control_id": "AC.L2-3.1.5",
                    },
                ],
                "objectives": [
                    {
                        "control_id": "AC.L2-3.1.1",
                        "objective_id": "a",
                        "objective_text": (
                            "Authorized users "
                            "are identified."
                        ),
                    },
                ],
                "guidance": [
                    {
                        "evidence_type": "Policy",
                        "description": (
                            "Provide the approved "
                            "Access Control Policy."
                        ),
                        "example_artifacts": [
                            "Access Control Policy",
                            (
                                "Identity and Access "
                                "Management Policy"
                            ),
                        ],
                        "required": True,
                    },
                ],
                "default_priority": "High",
                "suggested_owner": (
                    "Information Security"
                ),
                "sprs_weight": 5,
                "reuse_key": (
                    "ACCESS_CONTROL_POLICY"
                ),
                "tags": [
                    "Access Control",
                    "Governance",
                    "Policy",
                ],
                "source_reference": (
                    "CMMC Assessment Guide"
                ),
            }
        ],
    }


def test_template_creation() -> None:
    template = make_template()

    assert (
        template.template_id
        == "ACCESS_CONTROL_POLICY"
    )
    assert template.framework_id == "CMMC_L2"
    assert template.sprs_weight == 5

    assert (
        template.default_priority
        == EvidenceRequestPriority.HIGH
    )


def test_template_all_controls() -> None:
    template = make_template()

    assert template.control_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
        "AC.L2-3.1.5",
    )


def test_template_deduplicates_primary_control() -> None:
    template = EvidenceRequestTemplate(
        template_id="TEST",
        framework_id="CMMC_L2",
        title="Test Evidence",
        description="Provide test evidence.",
        category=EvidenceRequestCategory.OTHER,
        evidence_type=EvidenceRequestType.OTHER,
        primary_control=ControlReference(
            framework_id="CMMC_L2",
            control_id="AC.L2-3.1.1",
        ),
        related_controls=(
            ControlReference(
                framework_id="CMMC_L2",
                control_id="AC.L2-3.1.1",
            ),
            ControlReference(
                framework_id="CMMC_L2",
                control_id="AC.L2-3.1.2",
            ),
        ),
    )

    assert template.control_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    )


def test_template_requires_matching_framework() -> None:
    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestTemplate(
            template_id="TEST",
            framework_id="CMMC_L2",
            title="Test",
            description="Test evidence.",
            category=EvidenceRequestCategory.OTHER,
            evidence_type=EvidenceRequestType.OTHER,
            primary_control=ControlReference(
                framework_id="PCI_DSS_4_0",
                control_id="8.3.1",
            ),
        )


def test_blank_template_id_rejected() -> None:
    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        make_template(
            template_id=""
        )


def test_negative_sprs_weight_rejected() -> None:
    template = make_template()

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestTemplate(
            template_id="INVALID",
            framework_id="CMMC_L2",
            title="Invalid",
            description="Invalid evidence.",
            category=template.category,
            evidence_type=template.evidence_type,
            primary_control=template.primary_control,
            sprs_weight=-1,
        )


def test_empty_catalog() -> None:
    catalog = EvidenceRequestCatalog()

    assert catalog.count == 0
    assert catalog.templates() == []


def test_catalog_add() -> None:
    catalog = EvidenceRequestCatalog()

    catalog.add(
        make_template()
    )

    assert catalog.count == 1


def test_duplicate_template_rejected() -> None:
    catalog = EvidenceRequestCatalog()

    catalog.add(
        make_template()
    )

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        catalog.add(
            make_template()
        )


def test_get_template() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    template = catalog.get(
        "CMMC_L2",
        "ACCESS_CONTROL_POLICY",
    )

    assert (
        template.title
        == "Access Control Policy"
    )


def test_get_is_case_insensitive() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    template = catalog.get(
        "cmmc_l2",
        "access_control_policy",
    )

    assert (
        template.template_id
        == "ACCESS_CONTROL_POLICY"
    )


def test_get_unknown_template_raises() -> None:
    catalog = EvidenceRequestCatalog()

    with pytest.raises(
        EvidenceRequestCatalogNotFoundError
    ):
        catalog.get(
            "CMMC_L2",
            "DOES_NOT_EXIST",
        )


def test_find_returns_none_for_unknown() -> None:
    catalog = EvidenceRequestCatalog()

    assert (
        catalog.find(
            "CMMC_L2",
            "DOES_NOT_EXIST",
        )
        is None
    )


def test_for_framework() -> None:
    catalog = EvidenceRequestCatalog(
        [
            make_template(),
            make_template(
                template_id="PCI_AUTH",
                framework_id="PCI_DSS_4_0",
                primary_control_id="8.3.1",
                title="Authentication Evidence",
                reuse_key="AUTHENTICATION",
            ),
        ]
    )

    results = catalog.for_framework(
        "CMMC_L2"
    )

    assert len(results) == 1
    assert (
        results[0].template_id
        == "ACCESS_CONTROL_POLICY"
    )


def test_for_control_matches_primary_control() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.for_control(
        "CMMC_L2",
        "AC.L2-3.1.1",
    )

    assert len(results) == 1


def test_for_control_matches_related_control() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.for_control(
        "CMMC_L2",
        "AC.L2-3.1.5",
    )

    assert len(results) == 1


def test_for_control_unknown_returns_empty() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    assert (
        catalog.for_control(
            "CMMC_L2",
            "AU.L2-3.3.1",
        )
        == []
    )


def test_for_objective() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.for_objective(
        "CMMC_L2",
        "AC.L2-3.1.1",
        "a",
    )

    assert len(results) == 1


def test_for_objective_case_insensitive() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.for_objective(
        "cmmc_l2",
        "ac.l2-3.1.1",
        "A",
    )

    assert len(results) == 1


def test_for_reuse_key() -> None:
    catalog = EvidenceRequestCatalog(
        [
            make_template(),
            make_template(
                template_id=(
                    "ACCESS_CONTROL_PROCEDURE"
                ),
                primary_control_id="AC.L2-3.1.2",
                title="Access Control Procedure",
                reuse_key="ACCESS_CONTROL_POLICY",
            ),
        ]
    )

    results = catalog.for_reuse_key(
        "ACCESS_CONTROL_POLICY"
    )

    assert len(results) == 2


def test_blank_reuse_key_returns_empty() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    assert catalog.for_reuse_key("") == []


def test_for_tag() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.for_tag(
        "governance"
    )

    assert len(results) == 1


def test_search_title() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.search(
        "access control policy"
    )

    assert len(results) == 1


def test_search_description() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.search(
        "approved access"
    )

    assert len(results) == 1


def test_search_guidance() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.search(
        "identity and access management"
    )

    assert len(results) == 1


def test_search_control_id() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    results = catalog.search(
        "AC.L2-3.1.5"
    )

    assert len(results) == 1


def test_search_framework_filter() -> None:
    catalog = EvidenceRequestCatalog(
        [
            make_template(),
            make_template(
                template_id="PCI_POLICY",
                framework_id="PCI_DSS_4_0",
                primary_control_id="8.3.1",
                title="Access Control Policy",
                reuse_key="ACCESS_CONTROL_POLICY",
            ),
        ]
    )

    results = catalog.search(
        "access control",
        framework_id="CMMC_L2",
    )

    assert len(results) == 1
    assert (
        results[0].framework_id
        == "CMMC_L2"
    )


def test_blank_search_returns_empty() -> None:
    catalog = EvidenceRequestCatalog(
        [make_template()]
    )

    assert catalog.search("") == []


def test_from_mapping() -> None:
    catalog = EvidenceRequestCatalog.from_mapping(
        make_mapping()
    )

    assert catalog.count == 1

    template = catalog.get(
        "CMMC_L2",
        "ACCESS_CONTROL_POLICY",
    )

    assert template.sprs_weight == 5
    assert (
        template.suggested_owner
        == "Information Security"
    )
    assert len(template.guidance) == 1


def test_from_mapping_rejects_bad_schema() -> None:
    data = make_mapping()
    data["schema_version"] = "99.0"

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_from_mapping_requires_framework() -> None:
    data = make_mapping()
    data["framework_id"] = ""

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_from_mapping_requires_template_list() -> None:
    data = make_mapping()
    data["templates"] = {}

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_from_mapping_invalid_category() -> None:
    data = make_mapping()

    data["templates"][0][
        "category"
    ] = "Invalid Category"

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_from_mapping_invalid_evidence_type() -> None:
    data = make_mapping()

    data["templates"][0][
        "evidence_type"
    ] = "Invalid Type"

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_from_mapping_invalid_priority() -> None:
    data = make_mapping()

    data["templates"][0][
        "default_priority"
    ] = "Emergency"

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_mapping(
            data
        )


def test_json_catalog_loading(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "evidence_catalog.json"
    )

    path.write_text(
        json.dumps(
            make_mapping()
        ),
        encoding="utf-8",
    )

    catalog = EvidenceRequestCatalog.from_file(
        path
    )

    assert catalog.count == 1


def test_missing_catalog_file() -> None:
    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_file(
            "does_not_exist.json"
        )


def test_unsupported_catalog_extension(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "catalog.txt"
    )

    path.write_text(
        "catalog",
        encoding="utf-8",
    )

    with pytest.raises(
        EvidenceRequestCatalogError
    ):
        EvidenceRequestCatalog.from_file(
            path
        )


def test_template_tags_are_deduplicated() -> None:
    template = EvidenceRequestTemplate(
        template_id="TEST",
        framework_id="CMMC_L2",
        title="Test",
        description="Test evidence.",
        category=EvidenceRequestCategory.OTHER,
        evidence_type=EvidenceRequestType.OTHER,
        primary_control=ControlReference(
            framework_id="CMMC_L2",
            control_id="AC.L2-3.1.1",
        ),
        tags=(
            "Policy",
            "policy",
            "",
            "Governance",
        ),
    )

    assert template.tags == (
        "Policy",
        "Governance",
    )


def test_non_cmmc_framework_supported() -> None:
    template = make_template(
        template_id="PCI_AUTH_EVIDENCE",
        framework_id="PCI_DSS_4_0",
        primary_control_id="8.3.1",
        title="Authentication Evidence",
        reuse_key="AUTHENTICATION",
    )

    catalog = EvidenceRequestCatalog(
        [template]
    )

    result = catalog.get(
        "PCI_DSS_4_0",
        "PCI_AUTH_EVIDENCE",
    )

    assert (
        result.primary_control.control_id
        == "8.3.1"
    )