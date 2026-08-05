from __future__ import annotations

import pytest

from src.workbook.assessment_sync import (
    AssessmentRecord,
)
from src.workbook.dashboard_sync import (
    DashboardMetrics,
    DashboardSynchronizer,
)
from src.workbook.evidence_sync import (
    EvidenceCoverage,
)
from src.workbook.poam_sync import (
    POAMSyncResult,
)


def make_assessment_record(
    requirement_id: str,
    status: str,
    *,
    applicable: bool = True,
) -> AssessmentRecord:
    return AssessmentRecord(
        requirement_id=requirement_id,
        title=f"Requirement {requirement_id}",
        domain=requirement_id.split(".")[0],
        status=status,
        implementation_state="",
        applicable=applicable,
        owner="",
        evidence_status="",
        row_number=6,
    )


def make_evidence_coverage(
    *,
    total_evidence: int = 4,
    covered_requirements: int = 3,
    uncovered_requirements: int = 1,
    orphaned_evidence: int = 1,
    duplicate_evidence: int = 0,
) -> EvidenceCoverage:
    return EvidenceCoverage(
        total_evidence=total_evidence,
        covered_requirements=covered_requirements,
        uncovered_requirements=uncovered_requirements,
        orphaned_evidence=orphaned_evidence,
        duplicate_evidence=duplicate_evidence,
    )


def make_poam_result(
    *,
    final_poam_count: int = 1,
    created_count: int = 1,
    updated_count: int = 0,
    cleared_count: int = 0,
) -> POAMSyncResult:
    return POAMSyncResult(
        assessment_record_count=4,
        not_met_count=final_poam_count,
        existing_poam_count=updated_count,
        created_count=created_count,
        updated_count=updated_count,
        cleared_count=cleared_count,
        final_poam_count=final_poam_count,
    )


def sample_assessment_records() -> list[AssessmentRecord]:
    return [
        make_assessment_record(
            "AC.L2-3.1.1",
            "MET",
        ),
        make_assessment_record(
            "AU.L2-3.3.1",
            "NOT MET",
        ),
        make_assessment_record(
            "IA.L2-3.5.1",
            "NOT ASSESSED",
        ),
        make_assessment_record(
            "PE.L2-3.10.1",
            "NOT APPLICABLE",
            applicable=False,
        ),
    ]


def test_synchronize_returns_dashboard_metrics() -> None:
    synchronizer = DashboardSynchronizer()

    metrics = synchronizer.synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    assert isinstance(
        metrics,
        DashboardMetrics,
    )


def test_total_requirement_count() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    assert metrics.total_requirements == 4


def test_applicable_requirement_count() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    assert metrics.applicable_requirements == 3


def test_status_counts() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    assert metrics.met_requirements == 1
    assert metrics.not_met_requirements == 1
    assert metrics.not_assessed_requirements == 1


def test_assessment_completion_percentage() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    # Two of the three applicable requirements have
    # final findings: one MET and one NOT MET.
    assert (
        metrics.assessment_completion_percent
        == 66.67
    )


def test_certification_readiness_percentage() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(),
    )

    # One of three applicable requirements is MET.
    assert (
        metrics.certification_readiness_percent
        == 33.33
    )


def test_evidence_metrics() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(
            total_evidence=8,
            covered_requirements=75,
            uncovered_requirements=35,
            orphaned_evidence=2,
            duplicate_evidence=1,
        ),
        make_poam_result(),
    )

    assert metrics.evidence_total == 8
    assert metrics.orphaned_evidence == 2
    assert metrics.duplicate_evidence == 1


def test_evidence_coverage_percentage() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(
            covered_requirements=3,
            uncovered_requirements=1,
        ),
        make_poam_result(),
    )

    assert metrics.evidence_coverage_percent == 75.0


def test_poam_metrics() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(),
        make_poam_result(
            final_poam_count=3,
            created_count=2,
            updated_count=1,
            cleared_count=1,
        ),
    )

    assert metrics.poam_total == 3
    assert metrics.poam_created == 2
    assert metrics.poam_updated == 1
    assert metrics.poam_cleared == 1


@pytest.mark.parametrize(
    ("status", "expected_attribute"),
    [
        ("MET", "met_requirements"),
        ("met", "met_requirements"),
        ("NOT MET", "not_met_requirements"),
        ("not_met", "not_met_requirements"),
        (
            "NOT ASSESSED",
            "not_assessed_requirements",
        ),
        (
            "not_assessed",
            "not_assessed_requirements",
        ),
        (
            "PARTIALLY ASSESSED",
            "not_assessed_requirements",
        ),
        (
            "partially_assessed",
            "not_assessed_requirements",
        ),
    ],
)
def test_status_normalization(
    status: str,
    expected_attribute: str,
) -> None:
    record = make_assessment_record(
        "AC.L2-3.1.1",
        status,
    )

    metrics = DashboardSynchronizer().synchronize(
        [record],
        make_evidence_coverage(
            total_evidence=0,
            covered_requirements=0,
            uncovered_requirements=1,
            orphaned_evidence=0,
            duplicate_evidence=0,
        ),
        make_poam_result(
            final_poam_count=0,
            created_count=0,
        ),
    )

    assert (
        getattr(metrics, expected_attribute)
        == 1
    )


def test_all_met_produces_full_completion_and_readiness() -> None:
    records = [
        make_assessment_record(
            "AC.L2-3.1.1",
            "MET",
        ),
        make_assessment_record(
            "AU.L2-3.3.1",
            "MET",
        ),
        make_assessment_record(
            "IA.L2-3.5.1",
            "MET",
        ),
    ]

    metrics = DashboardSynchronizer().synchronize(
        records,
        make_evidence_coverage(
            covered_requirements=3,
            uncovered_requirements=0,
        ),
        make_poam_result(
            final_poam_count=0,
            created_count=0,
        ),
    )

    assert (
        metrics.assessment_completion_percent
        == 100.0
    )
    assert (
        metrics.certification_readiness_percent
        == 100.0
    )
    assert metrics.evidence_coverage_percent == 100.0


def test_all_not_met_is_complete_but_not_ready() -> None:
    records = [
        make_assessment_record(
            "AC.L2-3.1.1",
            "NOT MET",
        ),
        make_assessment_record(
            "AU.L2-3.3.1",
            "NOT MET",
        ),
    ]

    metrics = DashboardSynchronizer().synchronize(
        records,
        make_evidence_coverage(),
        make_poam_result(
            final_poam_count=2,
            created_count=2,
        ),
    )

    assert (
        metrics.assessment_completion_percent
        == 100.0
    )
    assert (
        metrics.certification_readiness_percent
        == 0.0
    )
    assert metrics.not_met_requirements == 2
    assert metrics.poam_total == 2


def test_no_assessment_records_returns_zero_percentages() -> None:
    metrics = DashboardSynchronizer().synchronize(
        [],
        make_evidence_coverage(
            total_evidence=0,
            covered_requirements=0,
            uncovered_requirements=0,
            orphaned_evidence=0,
            duplicate_evidence=0,
        ),
        make_poam_result(
            final_poam_count=0,
            created_count=0,
        ),
    )

    assert metrics.total_requirements == 0
    assert metrics.applicable_requirements == 0
    assert metrics.met_requirements == 0
    assert metrics.not_met_requirements == 0
    assert metrics.not_assessed_requirements == 0
    assert (
        metrics.assessment_completion_percent
        == 0.0
    )
    assert (
        metrics.certification_readiness_percent
        == 0.0
    )
    assert metrics.evidence_coverage_percent == 0.0


def test_no_applicable_requirements_returns_zero_percentages() -> None:
    records = [
        make_assessment_record(
            "PE.L2-3.10.1",
            "NOT APPLICABLE",
            applicable=False,
        ),
        make_assessment_record(
            "PE.L2-3.10.2",
            "NOT APPLICABLE",
            applicable=False,
        ),
    ]

    metrics = DashboardSynchronizer().synchronize(
        records,
        make_evidence_coverage(),
        make_poam_result(
            final_poam_count=0,
            created_count=0,
        ),
    )

    assert metrics.total_requirements == 2
    assert metrics.applicable_requirements == 0
    assert (
        metrics.assessment_completion_percent
        == 0.0
    )
    assert (
        metrics.certification_readiness_percent
        == 0.0
    )


def test_no_evidence_requirements_returns_zero_coverage() -> None:
    metrics = DashboardSynchronizer().synchronize(
        sample_assessment_records(),
        make_evidence_coverage(
            total_evidence=0,
            covered_requirements=0,
            uncovered_requirements=0,
            orphaned_evidence=0,
            duplicate_evidence=0,
        ),
        make_poam_result(),
    )

    assert metrics.evidence_total == 0
    assert metrics.evidence_coverage_percent == 0.0


def test_percentages_are_rounded_to_two_decimals() -> None:
    records = [
        make_assessment_record(
            "AC.L2-3.1.1",
            "MET",
        ),
        make_assessment_record(
            "AU.L2-3.3.1",
            "NOT ASSESSED",
        ),
        make_assessment_record(
            "IA.L2-3.5.1",
            "NOT ASSESSED",
        ),
    ]

    metrics = DashboardSynchronizer().synchronize(
        records,
        make_evidence_coverage(
            covered_requirements=1,
            uncovered_requirements=2,
        ),
        make_poam_result(
            final_poam_count=0,
            created_count=0,
        ),
    )

    assert (
        metrics.assessment_completion_percent
        == 33.33
    )
    assert (
        metrics.certification_readiness_percent
        == 33.33
    )
    assert metrics.evidence_coverage_percent == 33.33


def test_synchronize_accepts_assessment_iterable() -> None:
    records = sample_assessment_records()

    metrics = DashboardSynchronizer().synchronize(
        (
            record
            for record in records
        ),
        make_evidence_coverage(),
        make_poam_result(),
    )

    assert metrics.total_requirements == 4
    assert metrics.applicable_requirements == 3