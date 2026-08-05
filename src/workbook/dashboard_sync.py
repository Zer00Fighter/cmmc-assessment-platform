from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.workbook.assessment_sync import AssessmentRecord
from src.workbook.evidence_sync import EvidenceCoverage
from src.workbook.poam_sync import POAMSyncResult


class DashboardSyncError(Exception):
    """Raised when dashboard synchronization fails."""


@dataclass(frozen=True)
class DashboardMetrics:
    total_requirements: int
    applicable_requirements: int
    met_requirements: int
    not_met_requirements: int
    not_assessed_requirements: int

    assessment_completion_percent: float

    evidence_total: int
    evidence_coverage_percent: float
    orphaned_evidence: int
    duplicate_evidence: int

    poam_total: int
    poam_created: int
    poam_updated: int
    poam_cleared: int

    certification_readiness_percent: float


class DashboardSynchronizer:
    """
    Produces dashboard metrics from normalized data.

    This class contains NO Excel code.
    """

    def synchronize(
        self,
        assessment_records: Iterable[AssessmentRecord],
        evidence: EvidenceCoverage,
        poam: POAMSyncResult,
    ) -> DashboardMetrics:

        assessment_records = list(
            assessment_records
        )

        total = len(
            assessment_records
        )

        applicable = sum(
            record.applicable
            for record in assessment_records
        )

        met = sum(
            self._status(record) == "MET"
            for record in assessment_records
        )

        not_met = sum(
            self._status(record) == "NOT MET"
            for record in assessment_records
        )

        not_assessed = sum(
            self._status(record)
            in {
                "NOT ASSESSED",
                "PARTIALLY ASSESSED",
            }
            for record in assessment_records
        )

        completion = (
            0.0
            if applicable == 0
            else (
                (met + not_met)
                / applicable
            )
            * 100.0
        )

        coverage = (
            0.0
            if (
                evidence.covered_requirements
                + evidence.uncovered_requirements
            )
            == 0
            else (
                evidence.covered_requirements
                /
                (
                    evidence.covered_requirements
                    + evidence.uncovered_requirements
                )
            )
            * 100.0
        )

        readiness = (
            0.0
            if applicable == 0
            else (
                met
                / applicable
            )
            * 100.0
        )

        return DashboardMetrics(
            total_requirements=total,
            applicable_requirements=applicable,
            met_requirements=met,
            not_met_requirements=not_met,
            not_assessed_requirements=not_assessed,
            assessment_completion_percent=round(
                completion,
                2,
            ),
            evidence_total=evidence.total_evidence,
            evidence_coverage_percent=round(
                coverage,
                2,
            ),
            orphaned_evidence=evidence.orphaned_evidence,
            duplicate_evidence=evidence.duplicate_evidence,
            poam_total=poam.final_poam_count,
            poam_created=poam.created_count,
            poam_updated=poam.updated_count,
            poam_cleared=poam.cleared_count,
            certification_readiness_percent=round(
                readiness,
                2,
            ),
        )

    @staticmethod
    def _status(
        record: AssessmentRecord,
    ) -> str:
        return (
            record.status
            .strip()
            .upper()
            .replace("_", " ")
        )