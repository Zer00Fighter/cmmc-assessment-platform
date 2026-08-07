from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.evidence_requests.request_model import (
    ControlReference,
    EvidenceGuidance,
    EvidenceRequest,
    EvidenceRequestCategory,
    EvidenceRequestModelError,
    EvidenceRequestPriority,
    EvidenceRequestStatus,
    EvidenceRequestType,
    ObjectiveReference,
)


def make_control(
    control_id: str = "AC.L2-3.1.1",
) -> ControlReference:
    return ControlReference(
        framework_id="CMMC_L2",
        control_id=control_id,
        control_title=f"Control {control_id}",
    )


def make_request(
    **overrides,
) -> EvidenceRequest:
    values = {
        "request_id": "REQ-0001",
        "title": "Access Control Policy",
        "description": (
            "Provide the current access control policy "
            "and supporting implementation evidence."
        ),
        "category": (
            EvidenceRequestCategory.SYSTEM_DESIGN
        ),
        "evidence_type": (
            EvidenceRequestType.POLICY
        ),
        "primary_control": make_control(),
    }

    values.update(overrides)

    return EvidenceRequest(**values)


def test_control_reference_creation() -> None:
    control = make_control()

    assert control.framework_id == "CMMC_L2"
    assert control.control_id == "AC.L2-3.1.1"
    assert (
        control.control_title
        == "Control AC.L2-3.1.1"
    )


def test_control_reference_trims_values() -> None:
    control = ControlReference(
        framework_id=" CMMC_L2 ",
        control_id=" AC.L2-3.1.1 ",
        control_title=" Access Control ",
    )

    assert control.framework_id == "CMMC_L2"
    assert control.control_id == "AC.L2-3.1.1"
    assert control.control_title == "Access Control"


def test_blank_framework_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        ControlReference(
            framework_id="",
            control_id="AC.L2-3.1.1",
        )


def test_blank_control_id_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        ControlReference(
            framework_id="CMMC_L2",
            control_id="",
        )


def test_objective_reference_creation() -> None:
    objective = ObjectiveReference(
        framework_id="CMMC_L2",
        control_id="AC.L2-3.1.1",
        objective_id="a",
        objective_text=(
            "Authorized users are identified."
        ),
    )

    assert objective.framework_id == "CMMC_L2"
    assert objective.control_id == "AC.L2-3.1.1"
    assert objective.objective_id == "a"
    assert (
        objective.objective_text
        == "Authorized users are identified."
    )


def test_blank_objective_id_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        ObjectiveReference(
            framework_id="CMMC_L2",
            control_id="AC.L2-3.1.1",
            objective_id="",
        )


def test_evidence_guidance_creation() -> None:
    guidance = EvidenceGuidance(
        evidence_type=(
            EvidenceRequestType.CONFIGURATION
        ),
        description=(
            "Provide configuration showing "
            "authorized access restrictions."
        ),
        example_artifacts=[
            "Active Directory configuration",
            "Firewall rules",
        ],
    )

    assert (
        guidance.evidence_type
        == EvidenceRequestType.CONFIGURATION
    )

    assert len(guidance.example_artifacts) == 2

    assert guidance.required is True


def test_evidence_guidance_removes_blank_examples() -> None:
    guidance = EvidenceGuidance(
        evidence_type=EvidenceRequestType.POLICY,
        description="Provide policy.",
        example_artifacts=[
            "Access Control Policy",
            "",
            "   ",
        ],
    )

    assert guidance.example_artifacts == (
        "Access Control Policy",
    )


def test_blank_guidance_description_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        EvidenceGuidance(
            evidence_type=EvidenceRequestType.POLICY,
            description="",
        )


def test_request_creation() -> None:
    request = make_request()

    assert request.request_id == "REQ-0001"
    assert request.title == "Access Control Policy"

    assert (
        request.status
        == EvidenceRequestStatus.NOT_REQUESTED
    )

    assert (
        request.priority
        == EvidenceRequestPriority.MEDIUM
    )

    assert request.generated is True


def test_request_blank_id_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            request_id=""
        )


def test_request_blank_title_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            title=""
        )


def test_request_blank_description_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            description=""
        )


def test_negative_sprs_weight_is_rejected() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            sprs_weight=-1
        )


def test_valid_sprs_weight_is_allowed() -> None:
    request = make_request(
        sprs_weight=5
    )

    assert request.sprs_weight == 5


def test_primary_control_is_in_all_controls() -> None:
    request = make_request()

    assert request.control_ids == [
        "AC.L2-3.1.1"
    ]

    assert request.coverage_count == 1


def test_related_controls_are_in_all_controls() -> None:
    request = make_request(
        related_controls=[
            make_control("AC.L2-3.1.2"),
            make_control("AC.L2-3.1.5"),
        ]
    )

    assert request.control_ids == [
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
        "AC.L2-3.1.5",
    ]

    assert request.related_control_count == 2
    assert request.coverage_count == 3


def test_duplicate_related_controls_are_removed() -> None:
    request = make_request(
        related_controls=[
            make_control("AC.L2-3.1.2"),
            make_control("AC.L2-3.1.2"),
            make_control("AC.L2-3.1.5"),
        ]
    )

    assert request.control_ids == [
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
        "AC.L2-3.1.5",
    ]


def test_primary_control_is_not_duplicated() -> None:
    request = make_request(
        related_controls=[
            make_control("AC.L2-3.1.1"),
            make_control("AC.L2-3.1.2"),
        ]
    )

    assert request.control_ids == [
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    ]

    assert request.coverage_count == 2


def test_objective_ids_property() -> None:
    request = make_request(
        objectives=[
            ObjectiveReference(
                framework_id="CMMC_L2",
                control_id="AC.L2-3.1.1",
                objective_id="a",
            ),
            ObjectiveReference(
                framework_id="CMMC_L2",
                control_id="AC.L2-3.1.1",
                objective_id="b",
            ),
        ]
    )

    assert request.objective_ids == [
        "a",
        "b",
    ]


def test_duplicate_objectives_are_removed() -> None:
    objective = ObjectiveReference(
        framework_id="CMMC_L2",
        control_id="AC.L2-3.1.1",
        objective_id="a",
    )

    request = make_request(
        objectives=[
            objective,
            objective,
        ]
    )

    assert request.objective_ids == [
        "a"
    ]


def test_duplicate_tags_are_removed_case_insensitively() -> None:
    request = make_request(
        tags=[
            "Access Control",
            "Policy",
            "access control",
            "POLICY",
            "",
        ]
    )

    assert request.tags == [
        "Access Control",
        "Policy",
    ]


def test_mark_requested() -> None:
    request = make_request()

    requested = date(
        2026,
        8,
        1,
    )

    request.mark_requested(
        requested
    )

    assert (
        request.status
        == EvidenceRequestStatus.REQUESTED
    )

    assert request.requested_date == requested


def test_mark_received() -> None:
    request = make_request(
        requested_date=date(
            2026,
            8,
            1,
        )
    )

    received = date(
        2026,
        8,
        5,
    )

    request.mark_received(
        received
    )

    assert (
        request.status
        == EvidenceRequestStatus.RECEIVED
    )

    assert request.received_date == received
    assert request.is_received is True


def test_received_before_requested_is_rejected() -> None:
    request = make_request(
        requested_date=date(
            2026,
            8,
            10,
        )
    )

    with pytest.raises(
        EvidenceRequestModelError
    ):
        request.mark_received(
            date(
                2026,
                8,
                5,
            )
        )


def test_mark_in_review_requires_received_evidence() -> None:
    request = make_request()

    with pytest.raises(
        EvidenceRequestModelError
    ):
        request.mark_in_review()


def test_mark_in_review() -> None:
    request = make_request(
        received_date=date(
            2026,
            8,
            5,
        ),
        status=EvidenceRequestStatus.RECEIVED,
    )

    request.mark_in_review()

    assert (
        request.status
        == EvidenceRequestStatus.IN_REVIEW
    )

    assert request.is_received is True


def test_mark_accepted_requires_received_evidence() -> None:
    request = make_request()

    with pytest.raises(
        EvidenceRequestModelError
    ):
        request.mark_accepted()


def test_mark_accepted() -> None:
    request = make_request(
        received_date=date(
            2026,
            8,
            5,
        )
    )

    accepted = date(
        2026,
        8,
        6,
    )

    request.mark_accepted(
        accepted
    )

    assert (
        request.status
        == EvidenceRequestStatus.ACCEPTED
    )

    assert request.accepted_date == accepted
    assert request.is_accepted is True
    assert request.is_received is True
    assert request.is_open is False


def test_acceptance_before_receipt_is_rejected() -> None:
    request = make_request(
        received_date=date(
            2026,
            8,
            10,
        )
    )

    with pytest.raises(
        EvidenceRequestModelError
    ):
        request.mark_accepted(
            date(
                2026,
                8,
                5,
            )
        )


def test_mark_rejected() -> None:
    request = make_request()

    request.mark_rejected(
        "Screenshot does not show "
        "the required configuration."
    )

    assert (
        request.status
        == EvidenceRequestStatus.REJECTED_REPLACE
    )

    assert (
        request.assessor_notes
        == "Screenshot does not show "
        "the required configuration."
    )

    assert request.is_open is True


def test_mark_not_applicable() -> None:
    request = make_request()

    request.mark_not_applicable(
        "Wireless is not used."
    )

    assert (
        request.status
        == EvidenceRequestStatus.NOT_APPLICABLE
    )

    assert request.assessor_notes == (
        "Wireless is not used."
    )

    assert request.is_open is False


def test_overdue_property() -> None:
    request = make_request(
        due_date=(
            date.today()
            - timedelta(days=1)
        ),
        status=(
            EvidenceRequestStatus.PENDING_CLIENT
        ),
    )

    assert request.is_overdue is True


def test_future_due_date_is_not_overdue() -> None:
    request = make_request(
        due_date=(
            date.today()
            + timedelta(days=5)
        ),
        status=(
            EvidenceRequestStatus.PENDING_CLIENT
        ),
    )

    assert request.is_overdue is False


def test_accepted_request_is_not_overdue() -> None:
    request = make_request(
        due_date=(
            date.today()
            - timedelta(days=10)
        ),
        status=(
            EvidenceRequestStatus.ACCEPTED
        ),
        received_date=(
            date.today()
            - timedelta(days=12)
        ),
        accepted_date=(
            date.today()
            - timedelta(days=11)
        ),
    )

    assert request.is_overdue is False


def test_refresh_overdue_status() -> None:
    request = make_request(
        due_date=date(
            2026,
            8,
            5,
        ),
        status=(
            EvidenceRequestStatus.PENDING_CLIENT
        ),
    )

    request.refresh_overdue_status(
        as_of=date(
            2026,
            8,
            6,
        )
    )

    assert (
        request.status
        == EvidenceRequestStatus.OVERDUE
    )


def test_refresh_overdue_does_not_change_accepted() -> None:
    request = make_request(
        due_date=date(
            2026,
            8,
            1,
        ),
        status=(
            EvidenceRequestStatus.ACCEPTED
        ),
        received_date=date(
            2026,
            7,
            30,
        ),
        accepted_date=date(
            2026,
            7,
            31,
        ),
    )

    request.refresh_overdue_status(
        as_of=date(
            2026,
            8,
            6,
        )
    )

    assert (
        request.status
        == EvidenceRequestStatus.ACCEPTED
    )


def test_initial_date_validation() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            requested_date=date(
                2026,
                8,
                10,
            ),
            received_date=date(
                2026,
                8,
                5,
            ),
        )


def test_initial_acceptance_date_validation() -> None:
    with pytest.raises(
        EvidenceRequestModelError
    ):
        make_request(
            received_date=date(
                2026,
                8,
                10,
            ),
            accepted_date=date(
                2026,
                8,
                5,
            ),
        )


def test_evidence_request_enums_have_expected_values() -> None:
    assert (
        EvidenceRequestStatus.ACCEPTED.value
        == "Accepted"
    )

    assert (
        EvidenceRequestPriority.CRITICAL.value
        == "Critical"
    )

    assert (
        EvidenceRequestType.SCREENSHOT.value
        == "Screenshot"
    )

    assert (
        EvidenceRequestCategory.SYSTEM_DESIGN.value
        == "System Design Documentation"
    )


def test_non_cmmc_control_reference_is_supported() -> None:
    control = ControlReference(
        framework_id="PCI_DSS_4_0",
        control_id="8.3.1",
        control_title=(
            "Strong authentication "
            "for users and administrators"
        ),
    )

    request = make_request(
        primary_control=control,
        sprs_weight=None,
    )

    assert (
        request.primary_control.framework_id
        == "PCI_DSS_4_0"
    )

    assert (
        request.primary_control.control_id
        == "8.3.1"
    )