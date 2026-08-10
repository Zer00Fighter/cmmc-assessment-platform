from __future__ import annotations

import pytest

from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestControl,
    DocumentationRequestPriority,
    DocumentationRequestStatus,
    DocumentationRequestType,
)
from src.evidence_requests.request_optimizer import (
    RequestOptimizer,
    RequestOptimizerError,
)


def control(
    control_id: str,
    *,
    family: str = "AC",
) -> DocumentationRequestControl:
    return DocumentationRequestControl(
        framework_id="CMMC_L2",
        control_id=control_id,
        family=family,
    )


def request(
    request_id: str,
    title: str,
    controls: list[DocumentationRequestControl],
    *,
    evidence_type: DocumentationRequestType = (DocumentationRequestType.OTHER),
    priority: DocumentationRequestPriority = (DocumentationRequestPriority.LOW),
    description: str = "",
) -> DocumentationRequest:
    return DocumentationRequest(
        request_id=request_id,
        requested_item=title,
        evidence_type=evidence_type,
        priority=priority,
        controls=controls,
        description=description,
    )


def collection(
    requests: list[DocumentationRequest],
) -> DocumentationRequestCollection:
    return DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=requests,
    )


def test_optimizer_preserves_unique_control_coverage() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                    control("AC.L2-3.1.2"),
                ],
            ),
            request(
                "DRL-002",
                "Access Control Policy and Procedures",
                [
                    control("AC.L2-3.1.2"),
                    control("AC.L2-3.1.3"),
                ],
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert optimized.summary.unique_controls_supported == 3

    assert {item.control_id for item in optimized.requests[0].controls} == {
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
        "AC.L2-3.1.3",
    }


def test_access_control_policy_variants_merge() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
            request(
                "DRL-002",
                "Access Control Policy and Procedures",
                [
                    control("AC.L2-3.1.2"),
                ],
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert optimized.count == 1

    assert (
        optimized.requests[0].requested_item == "Access Control Policy and Procedures"
    )

    assert optimized.requests[0].evidence_type == DocumentationRequestType.POLICY


def test_account_lists_merge_into_inventory_package() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "List of System Accounts",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
            request(
                "DRL-002",
                "Privileged Account List",
                [
                    control("AC.L2-3.1.2"),
                ],
            ),
            request(
                "DRL-003",
                "Service Account List",
                [
                    control("AC.L2-3.1.3"),
                ],
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert optimized.count == 1

    assert (
        optimized.requests[0].requested_item
        == "System and Privileged Account Inventory"
    )

    assert optimized.requests[0].evidence_type == DocumentationRequestType.INVENTORY

    assert optimized.requests[0].reuse_count == 3


def test_evidence_resolver_merges_canonical_aliases() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "SSP",
                [control("CA.L2-3.12.4", family="CA")],
                evidence_type=(DocumentationRequestType.SYSTEM_SECURITY_PLAN),
            ),
            request(
                "DRL-002",
                "Information Security Plan",
                [control("CA.L2-3.12.1", family="CA")],
                evidence_type=(DocumentationRequestType.SYSTEM_SECURITY_PLAN),
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert optimized.count == 1
    assert optimized.requests[0].requested_item == "Security Plan"
    assert optimized.requests[0].reuse_count == 2
    assert "Resolved source wording" in (optimized.requests[0].description)


def test_generic_request_is_suppressed_when_redundant() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Other Relevant Documents or Records",
                [
                    control("AC.L2-3.1.1"),
                    control("AC.L2-3.1.2"),
                ],
            ),
            request(
                "DRL-002",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
            request(
                "DRL-003",
                "Account Inventory",
                [
                    control("AC.L2-3.1.2"),
                ],
                evidence_type=(DocumentationRequestType.INVENTORY),
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert "Other Relevant Documents or Records" not in {
        item.requested_item for item in optimized.requests
    }

    assert optimized.summary.unique_controls_supported == 2


def test_generic_request_is_kept_when_it_has_unique_control() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Other Relevant Documents or Records",
                [
                    control("AC.L2-3.1.1"),
                    control("AC.L2-3.1.2"),
                ],
            ),
            request(
                "DRL-002",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert "Other Relevant Documents or Records" in {
        item.requested_item for item in optimized.requests
    }

    assert optimized.summary.unique_controls_supported == 2


def test_optimizer_regenerates_deterministic_ids() -> None:
    raw = collection(
        [
            request(
                "OLD-900",
                "Z Evidence",
                [
                    control("AC.L2-3.1.2"),
                ],
            ),
            request(
                "OLD-100",
                "A Evidence",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert [item.request_id for item in optimized.requests] == [
        "DRL-001",
        "DRL-002",
    ]

    assert [item.requested_item for item in optimized.requests] == [
        "A Evidence",
        "Z Evidence",
    ]


def test_merge_preserves_highest_priority() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
                priority=(DocumentationRequestPriority.HIGH),
            ),
            request(
                "DRL-002",
                "Access Control Policy and Procedures",
                [
                    control("AC.L2-3.1.2"),
                ],
                priority=(DocumentationRequestPriority.LOW),
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    assert optimized.requests[0].priority == DocumentationRequestPriority.HIGH


def test_merge_preserves_source_descriptions() -> None:
    raw = collection(
        [
            request(
                "DRL-001",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
                description="Access control policy.",
            ),
            request(
                "DRL-002",
                "Access Control Policy and Procedures",
                [
                    control("AC.L2-3.1.2"),
                ],
                description="Access control procedures.",
            ),
        ]
    )

    optimized = RequestOptimizer().optimize(raw)

    description = optimized.requests[0].description

    assert "Access control policy." in description
    assert "Access control procedures." in description


def test_optimizer_does_not_mutate_input() -> None:
    raw = collection(
        [
            request(
                "ORIGINAL-001",
                "Access Control Policy",
                [
                    control("AC.L2-3.1.1"),
                ],
            ),
            request(
                "ORIGINAL-002",
                "Access Control Policy and Procedures",
                [
                    control("AC.L2-3.1.2"),
                ],
            ),
        ]
    )

    RequestOptimizer().optimize(raw)

    assert raw.count == 2

    assert [item.request_id for item in raw.requests] == [
        "ORIGINAL-001",
        "ORIGINAL-002",
    ]


def test_submitted_request_cannot_be_optimized() -> None:
    submitted = request(
        "DRL-001",
        "Access Control Policy",
        [
            control("AC.L2-3.1.1"),
        ],
    )

    submitted.mark_submitted(file_name="policy.pdf")

    raw = collection(
        [
            submitted,
        ]
    )

    with pytest.raises(
        RequestOptimizerError,
        match="Submitted DRL requests cannot be optimized",
    ):
        RequestOptimizer().optimize(raw)


def test_progressed_request_cannot_be_optimized() -> None:
    progressed = request(
        "DRL-001",
        "Access Control Policy",
        [
            control("AC.L2-3.1.1"),
        ],
    )

    progressed.review_status = DocumentationRequestStatus.REQUESTED

    raw = collection(
        [
            progressed,
        ]
    )

    with pytest.raises(
        RequestOptimizerError,
        match="Only untouched generated DRLs can be optimized",
    ):
        RequestOptimizer().optimize(raw)
