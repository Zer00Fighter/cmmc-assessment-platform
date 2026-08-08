from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.evidence_requests.drl_model import (
    DRLModelError,
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestControl,
    DocumentationRequestPriority,
    DocumentationRequestStatus,
    DocumentationRequestType,
)


def make_control(
    control_id: str = "AC.L2-3.1.1",
    *,
    framework_id: str = "CMMC_L2",
    family: str = "AC",
) -> DocumentationRequestControl:
    return DocumentationRequestControl(
        framework_id=framework_id,
        control_id=control_id,
        family=family,
        control_title=f"Control {control_id}",
    )


def make_request(
    *,
    request_id: str = "DRL-0001",
    requested_item: str = "Access Control Policy",
    evidence_type: DocumentationRequestType = (
        DocumentationRequestType.POLICY
    ),
    priority: DocumentationRequestPriority = (
        DocumentationRequestPriority.HIGH
    ),
    controls=None,
    **kwargs,
) -> DocumentationRequest:
    if controls is None:
        controls = [
            make_control(),
        ]

    return DocumentationRequest(
        request_id=request_id,
        requested_item=requested_item,
        evidence_type=evidence_type,
        priority=priority,
        controls=controls,
        **kwargs,
    )


def test_control_creation() -> None:
    control = make_control()

    assert control.framework_id == "CMMC_L2"
    assert control.control_id == "AC.L2-3.1.1"
    assert control.family == "AC"


def test_control_values_are_trimmed() -> None:
    control = DocumentationRequestControl(
        framework_id=" CMMC_L2 ",
        control_id=" AC.L2-3.1.1 ",
        family=" AC ",
        control_title=" Access Control ",
    )

    assert control.framework_id == "CMMC_L2"
    assert control.control_id == "AC.L2-3.1.1"
    assert control.family == "AC"
    assert control.control_title == "Access Control"


def test_control_requires_framework() -> None:
    with pytest.raises(DRLModelError):
        DocumentationRequestControl(
            framework_id="",
            control_id="AC.L2-3.1.1",
        )


def test_control_requires_control_id() -> None:
    with pytest.raises(DRLModelError):
        DocumentationRequestControl(
            framework_id="CMMC_L2",
            control_id="",
        )


def test_control_key_is_case_insensitive() -> None:
    first = make_control()

    second = DocumentationRequestControl(
        framework_id="cmmc_l2",
        control_id="ac.l2-3.1.1",
    )

    assert first.key == second.key


def test_request_creation() -> None:
    request = make_request()

    assert request.request_id == "DRL-0001"
    assert request.requested_item == "Access Control Policy"
    assert request.evidence_type == DocumentationRequestType.POLICY
    assert request.priority == DocumentationRequestPriority.HIGH
    assert request.submitted is False
    assert request.generated is True


def test_request_requires_id() -> None:
    with pytest.raises(DRLModelError):
        make_request(
            request_id="",
        )


def test_request_requires_requested_item() -> None:
    with pytest.raises(DRLModelError):
        make_request(
            requested_item="",
        )


def test_request_text_values_are_trimmed() -> None:
    request = make_request(
        request_id=" DRL-0001 ",
        requested_item=" Access Control Policy ",
        description=" Provide approved policy. ",
        current_version=" v2.1 ",
        file_name=" policy.pdf ",
        evidence_location=" SharePoint ",
        reviewer=" Assessor One ",
        comments=" Looks good. ",
        client_poc=" Jane Doe ",
    )

    assert request.request_id == "DRL-0001"
    assert request.requested_item == "Access Control Policy"
    assert request.description == "Provide approved policy."
    assert request.current_version == "v2.1"
    assert request.file_name == "policy.pdf"
    assert request.evidence_location == "SharePoint"
    assert request.reviewer == "Assessor One"
    assert request.comments == "Looks good."
    assert request.client_poc == "Jane Doe"


def test_duplicate_controls_are_removed() -> None:
    request = make_request(
        controls=[
            make_control("AC.L2-3.1.1"),
            make_control("AC.L2-3.1.1"),
            make_control("AC.L2-3.1.2"),
        ]
    )

    assert request.control_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    )


def test_control_ids_property() -> None:
    request = make_request(
        controls=[
            make_control("AC.L2-3.1.1"),
            make_control("AC.L2-3.1.2"),
        ]
    )

    assert request.control_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    )


def test_framework_ids_property() -> None:
    request = make_request(
        controls=[
            make_control(
                "AC.L2-3.1.1",
                framework_id="CMMC_L2",
            ),
            make_control(
                "8.3.1",
                framework_id="PCI_DSS_4_0",
                family="8",
            ),
            make_control(
                "AC.L2-3.1.2",
                framework_id="cmmc_l2",
            ),
        ]
    )

    assert request.framework_ids == (
        "CMMC_L2",
        "PCI_DSS_4_0",
    )


def test_control_families_property() -> None:
    request = make_request(
        controls=[
            make_control(
                "AC.L2-3.1.1",
                family="AC",
            ),
            make_control(
                "AU.L2-3.3.1",
                family="AU",
            ),
            make_control(
                "AC.L2-3.1.2",
                family="ac",
            ),
        ]
    )

    assert request.control_families == (
        "AC",
        "AU",
    )


def test_reuse_count() -> None:
    request = make_request(
        controls=[
            make_control("AC.L2-3.1.1"),
            make_control("AC.L2-3.1.2"),
            make_control("AC.L2-3.1.5"),
        ]
    )

    assert request.reuse_count == 3
    assert request.is_reused is True


def test_single_control_is_not_reused() -> None:
    request = make_request()

    assert request.reuse_count == 1
    assert request.is_reused is False


def test_default_request_status() -> None:
    request = make_request()

    assert (
        request.review_status
        == DocumentationRequestStatus.NOT_REQUESTED
    )


def test_mark_requested() -> None:
    request = make_request()

    request.mark_requested()

    assert (
        request.review_status
        == DocumentationRequestStatus.REQUESTED
    )


def test_mark_submitted() -> None:
    request = make_request()

    submitted_date = date(
        2026,
        8,
        7,
    )

    request.mark_submitted(
        submitted_date=submitted_date,
        file_name="Access_Control_Policy.pdf",
        location="SharePoint/CMMC",
        version="3.0",
    )

    assert request.submitted is True
    assert request.date_submitted == submitted_date
    assert request.file_name == "Access_Control_Policy.pdf"
    assert request.evidence_location == "SharePoint/CMMC"
    assert request.current_version == "3.0"

    assert (
        request.review_status
        == DocumentationRequestStatus.SUBMITTED
    )


def test_under_review_requires_submission() -> None:
    request = make_request()

    with pytest.raises(DRLModelError):
        request.mark_under_review(
            reviewer="Assessor"
        )


def test_mark_under_review() -> None:
    request = make_request(
        submitted=True,
        date_submitted=date(
            2026,
            8,
            7,
        ),
        review_status=(
            DocumentationRequestStatus.SUBMITTED
        ),
    )

    request.mark_under_review(
        reviewer="Assessor One"
    )

    assert (
        request.review_status
        == DocumentationRequestStatus.UNDER_REVIEW
    )

    assert request.reviewer == "Assessor One"


def test_accept_requires_submission() -> None:
    request = make_request()

    with pytest.raises(DRLModelError):
        request.mark_accepted()


def test_mark_accepted() -> None:
    request = make_request(
        submitted=True,
        date_submitted=date(
            2026,
            8,
            5,
        ),
        review_status=(
            DocumentationRequestStatus.SUBMITTED
        ),
    )

    request.mark_accepted(
        reviewed_date=date(
            2026,
            8,
            7,
        ),
        reviewer="Lead Assessor",
        comments="Accepted.",
    )

    assert (
        request.review_status
        == DocumentationRequestStatus.ACCEPTED
    )

    assert request.date_reviewed == date(
        2026,
        8,
        7,
    )

    assert request.reviewer == "Lead Assessor"
    assert request.comments == "Accepted."
    assert request.is_complete is True


def test_review_date_before_submission_rejected() -> None:
    request = make_request(
        submitted=True,
        date_submitted=date(
            2026,
            8,
            10,
        ),
    )

    with pytest.raises(DRLModelError):
        request.mark_accepted(
            reviewed_date=date(
                2026,
                8,
                5,
            )
        )


def test_initial_review_date_before_submission_rejected() -> None:
    with pytest.raises(DRLModelError):
        make_request(
            submitted=True,
            date_submitted=date(
                2026,
                8,
                10,
            ),
            date_reviewed=date(
                2026,
                8,
                5,
            ),
        )


def test_needs_revision_requires_submission() -> None:
    request = make_request()

    with pytest.raises(DRLModelError):
        request.mark_needs_revision()


def test_mark_needs_revision() -> None:
    request = make_request(
        submitted=True,
        date_submitted=date(
            2026,
            8,
            5,
        ),
    )

    request.mark_needs_revision(
        reviewed_date=date(
            2026,
            8,
            7,
        ),
        reviewer="Assessor",
        comments="Please provide signed version.",
    )

    assert (
        request.review_status
        == DocumentationRequestStatus.NEEDS_REVISION
    )

    assert (
        request.comments
        == "Please provide signed version."
    )

    assert request.needs_client_action is True


def test_mark_not_applicable() -> None:
    request = make_request()

    request.mark_not_applicable(
        "Wireless capability is not in scope."
    )

    assert (
        request.review_status
        == DocumentationRequestStatus.NOT_APPLICABLE
    )

    assert (
        request.comments
        == "Wireless capability is not in scope."
    )

    assert request.needs_client_action is False


@pytest.mark.parametrize(
    "status",
    [
        DocumentationRequestStatus.NOT_REQUESTED,
        DocumentationRequestStatus.REQUESTED,
        DocumentationRequestStatus.PENDING,
        DocumentationRequestStatus.NEEDS_REVISION,
    ],
)
def test_client_action_statuses(
    status: DocumentationRequestStatus,
) -> None:
    request = make_request(
        review_status=status,
    )

    assert request.needs_client_action is True


@pytest.mark.parametrize(
    "status",
    [
        DocumentationRequestStatus.SUBMITTED,
        DocumentationRequestStatus.UNDER_REVIEW,
        DocumentationRequestStatus.ACCEPTED,
        DocumentationRequestStatus.NOT_APPLICABLE,
    ],
)
def test_non_client_action_statuses(
    status: DocumentationRequestStatus,
) -> None:
    request = make_request(
        review_status=status,
    )

    assert request.needs_client_action is False


def test_overdue_request() -> None:
    request = make_request(
        due_date=(
            date.today()
            - timedelta(days=1)
        ),
        review_status=(
            DocumentationRequestStatus.REQUESTED
        ),
    )

    assert request.is_overdue is True


def test_future_request_not_overdue() -> None:
    request = make_request(
        due_date=(
            date.today()
            + timedelta(days=10)
        ),
        review_status=(
            DocumentationRequestStatus.REQUESTED
        ),
    )

    assert request.is_overdue is False


def test_accepted_request_not_overdue() -> None:
    request = make_request(
        due_date=(
            date.today()
            - timedelta(days=20)
        ),
        submitted=True,
        date_submitted=(
            date.today()
            - timedelta(days=30)
        ),
        review_status=(
            DocumentationRequestStatus.ACCEPTED
        ),
    )

    assert request.is_overdue is False


def test_collection_requires_framework() -> None:
    with pytest.raises(DRLModelError):
        DocumentationRequestCollection(
            framework_id=""
        )


def test_empty_collection() -> None:
    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2"
    )

    assert collection.count == 0
    assert collection.requests == []


def test_collection_values_are_trimmed() -> None:
    collection = DocumentationRequestCollection(
        framework_id=" CMMC_L2 ",
        engagement_name=" Assessment 2026 ",
        organization_name=" ACME Corp ",
        assessor_organization=" C3PAO LLC ",
        notes=" Initial DRL ",
    )

    assert collection.framework_id == "CMMC_L2"
    assert collection.engagement_name == "Assessment 2026"
    assert collection.organization_name == "ACME Corp"
    assert collection.assessor_organization == "C3PAO LLC"
    assert collection.notes == "Initial DRL"


def test_collection_add() -> None:
    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2"
    )

    collection.add(
        make_request()
    )

    assert collection.count == 1


def test_collection_rejects_duplicate_request_ids() -> None:
    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2"
    )

    collection.add(
        make_request(
            request_id="DRL-0001"
        )
    )

    with pytest.raises(DRLModelError):
        collection.add(
            make_request(
                request_id="drl-0001"
            )
        )


def test_collection_constructor_rejects_duplicates() -> None:
    with pytest.raises(DRLModelError):
        DocumentationRequestCollection(
            framework_id="CMMC_L2",
            requests=[
                make_request(
                    request_id="DRL-0001"
                ),
                make_request(
                    request_id="drl-0001"
                ),
            ],
        )


def test_collection_get() -> None:
    request = make_request()

    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=[
            request
        ],
    )

    result = collection.get(
        "drl-0001"
    )

    assert result is request


def test_collection_get_unknown_raises() -> None:
    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2"
    )

    with pytest.raises(DRLModelError):
        collection.get(
            "DRL-9999"
        )


def test_collection_summary() -> None:
    first = make_request(
        request_id="DRL-0001",
        priority=(
            DocumentationRequestPriority.HIGH
        ),
        controls=[
            make_control(
                "AC.L2-3.1.1"
            ),
            make_control(
                "AC.L2-3.1.2"
            ),
        ],
        submitted=True,
        date_submitted=date(
            2026,
            8,
            1,
        ),
        review_status=(
            DocumentationRequestStatus.ACCEPTED
        ),
    )

    second = make_request(
        request_id="DRL-0002",
        requested_item="Audit Logs",
        evidence_type=(
            DocumentationRequestType.LOG
        ),
        priority=(
            DocumentationRequestPriority.MEDIUM
        ),
        controls=[
            make_control(
                "AU.L2-3.3.1",
                family="AU",
            )
        ],
        review_status=(
            DocumentationRequestStatus.REQUESTED
        ),
    )

    third = make_request(
        request_id="DRL-0003",
        requested_item="Network Diagram",
        evidence_type=(
            DocumentationRequestType.DIAGRAM
        ),
        priority=(
            DocumentationRequestPriority.LOW
        ),
        controls=[
            make_control(
                "SC.L2-3.13.1",
                family="SC",
            )
        ],
        submitted=True,
        date_submitted=date(
            2026,
            8,
            2,
        ),
        review_status=(
            DocumentationRequestStatus.UNDER_REVIEW
        ),
    )

    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=[
            first,
            second,
            third,
        ],
    )

    summary = collection.summary

    assert summary.total_requests == 3

    assert summary.high_priority == 1
    assert summary.medium_priority == 1
    assert summary.low_priority == 1

    assert summary.submitted == 2
    assert summary.accepted == 1
    assert summary.under_review == 1
    assert summary.pending == 1

    assert summary.unique_controls_supported == 4
    assert summary.reused_requests == 1
    assert summary.total_control_mappings == 4


def test_summary_counts_needs_revision() -> None:
    request = make_request(
        submitted=True,
        date_submitted=date(
            2026,
            8,
            1,
        ),
        review_status=(
            DocumentationRequestStatus.NEEDS_REVISION
        ),
    )

    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=[
            request
        ],
    )

    assert (
        collection.summary.needs_revision
        == 1
    )


def test_summary_counts_not_applicable() -> None:
    request = make_request(
        review_status=(
            DocumentationRequestStatus.NOT_APPLICABLE
        ),
    )

    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=[
            request
        ],
    )

    assert (
        collection.summary.not_applicable
        == 1
    )


def test_summary_counts_overdue_requests() -> None:
    request = make_request(
        due_date=(
            date.today()
            - timedelta(days=2)
        ),
        review_status=(
            DocumentationRequestStatus.REQUESTED
        ),
    )

    collection = DocumentationRequestCollection(
        framework_id="CMMC_L2",
        requests=[
            request
        ],
    )

    assert collection.summary.overdue == 1


def test_non_cmmc_request_supported() -> None:
    request = make_request(
        controls=[
            make_control(
                "8.3.1",
                framework_id="PCI_DSS_4_0",
                family="8",
            )
        ]
    )

    assert request.framework_ids == (
        "PCI_DSS_4_0",
    )


def test_enum_values() -> None:
    assert (
        DocumentationRequestStatus.ACCEPTED.value
        == "Accepted"
    )

    assert (
        DocumentationRequestPriority.HIGH.value
        == "High"
    )

    assert (
        DocumentationRequestType.SYSTEM_SECURITY_PLAN.value
        == "System Security Plan"
    )

    assert (
        DocumentationRequestType.INTERVIEW.value
        == "Interview"
    )

    assert (
        DocumentationRequestType.DEMONSTRATION.value
        == "Demonstration"
    )