from __future__ import annotations

from dataclasses import dataclass
from typing import List

from openpyxl.workbook.workbook import Workbook

from src.workbook.assessment_sync import (
    AssessmentRecord,
    AssessmentSynchronizer,
)
from src.workbook.dashboard_sync import (
    DashboardMetrics,
    DashboardSynchronizer,
)
from src.workbook.evidence_sync import (
    EvidenceCoverage,
    EvidenceRecord,
    EvidenceSynchronizer,
)
from src.workbook.formulas_sync import (
    FormulaSyncResult,
    FormulaSynchronizer,
)
from src.workbook.poam_sync import (
    POAMSyncResult,
    POAMWorksheetSynchronizer,
)


class WorkbookPipelineError(RuntimeError):
    """Raised when the workbook synchronization pipeline fails."""


@dataclass(frozen=True)
class WorkbookPipelineResult:
    """Complete result from one workbook synchronization run."""

    assessment_records: List[AssessmentRecord]
    evidence_records: List[EvidenceRecord]
    evidence_coverage: EvidenceCoverage
    poam_result: POAMSyncResult
    dashboard_metrics: DashboardMetrics
    formula_result: FormulaSyncResult

    @property
    def assessment_count(self) -> int:
        return len(self.assessment_records)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_records)

    @property
    def poam_count(self) -> int:
        return self.poam_result.final_poam_count


class WorkbookPipeline:
    """
    Run the complete workbook synchronization workflow.

    Pipeline order:

    1. Read normalized Assessment records.
    2. Read normalized Evidence records.
    3. Calculate evidence coverage.
    4. Synchronize NOT MET findings into POA&M.
    5. Calculate dashboard metrics.
    6. Restore workbook formulas.
    7. Configure automatic workbook recalculation.
    """

    REQUIRED_SHEETS = {
        "Assessment",
        "Evidence",
        "POA&M",
        "Dashboard",
    }

    def __init__(
        self,
        assessment_synchronizer: AssessmentSynchronizer | None = None,
        evidence_synchronizer: EvidenceSynchronizer | None = None,
        poam_synchronizer: POAMWorksheetSynchronizer | None = None,
        dashboard_synchronizer: DashboardSynchronizer | None = None,
        formula_synchronizer: FormulaSynchronizer | None = None,
    ) -> None:
        self.assessment_synchronizer = (
            assessment_synchronizer
            or AssessmentSynchronizer()
        )

        self.evidence_synchronizer = (
            evidence_synchronizer
            or EvidenceSynchronizer()
        )

        self.poam_synchronizer = (
            poam_synchronizer
            or POAMWorksheetSynchronizer()
        )

        self.dashboard_synchronizer = (
            dashboard_synchronizer
            or DashboardSynchronizer()
        )

        self.formula_synchronizer = (
            formula_synchronizer
            or FormulaSynchronizer()
        )

    def run(
        self,
        workbook: Workbook,
    ) -> WorkbookPipelineResult:
        """Run all synchronization stages against one workbook."""

        self._validate_workbook(workbook)

        assessment_sheet = workbook["Assessment"]
        evidence_sheet = workbook["Evidence"]
        poam_sheet = workbook["POA&M"]
        dashboard_sheet = workbook["Dashboard"]

        try:
            assessment_records = (
                self.assessment_synchronizer.synchronize(
                    assessment_sheet
                )
            )

            evidence_records = (
                self.evidence_synchronizer.synchronize(
                    evidence_sheet
                )
            )

            requirement_ids = [
                record.requirement_id
                for record in assessment_records
            ]

            evidence_coverage = (
                self.evidence_synchronizer.calculate_coverage(
                    evidence_records,
                    requirement_ids,
                )
            )

            poam_result = (
                self.poam_synchronizer.synchronize(
                    poam_sheet,
                    assessment_records,
                )
            )

            dashboard_metrics = (
                self.dashboard_synchronizer.synchronize(
                    assessment_records,
                    evidence_coverage,
                    poam_result,
                )
            )

            self._write_dashboard_metrics(
                dashboard_sheet,
                dashboard_metrics,
            )

            formula_result = (
                self.formula_synchronizer.synchronize(
                    assessment_sheet,
                    poam_sheet,
                    dashboard_sheet,
                )
            )

            self._configure_recalculation(
                workbook
            )

        except WorkbookPipelineError:
            raise

        except Exception as error:
            raise WorkbookPipelineError(
                "Workbook synchronization pipeline failed: "
                f"{error}"
            ) from error

        return WorkbookPipelineResult(
            assessment_records=assessment_records,
            evidence_records=evidence_records,
            evidence_coverage=evidence_coverage,
            poam_result=poam_result,
            dashboard_metrics=dashboard_metrics,
            formula_result=formula_result,
        )

    def synchronize(
        self,
        workbook: Workbook,
    ) -> WorkbookPipelineResult:
        """Alias for run(), used by higher-level callers."""

        return self.run(workbook)

    def _validate_workbook(
        self,
        workbook: Workbook,
    ) -> None:
        missing_sheets = (
            self.REQUIRED_SHEETS
            - set(workbook.sheetnames)
        )

        if missing_sheets:
            raise WorkbookPipelineError(
                "Workbook is missing required sheets: "
                + ", ".join(
                    sorted(missing_sheets)
                )
            )

    @staticmethod
    def _write_dashboard_metrics(
        dashboard_sheet,
        metrics: DashboardMetrics,
    ) -> None:
        """
        Write synchronized metrics to a dedicated dashboard area.

        These cells are separate from the existing formula cards so the
        current dashboard design remains compatible while the new
        synchronization pipeline is introduced.
        """

        values = {
            "B18": "Synchronized Metrics",
            "B19": "Total Requirements",
            "C19": metrics.total_requirements,
            "B20": "Applicable Requirements",
            "C20": metrics.applicable_requirements,
            "B21": "MET Requirements",
            "C21": metrics.met_requirements,
            "B22": "NOT MET Requirements",
            "C22": metrics.not_met_requirements,
            "B23": "NOT ASSESSED Requirements",
            "C23": metrics.not_assessed_requirements,
            "B24": "Assessment Completion",
            "C24": (
                metrics.assessment_completion_percent
                / 100
            ),
            "E19": "Evidence Records",
            "F19": metrics.evidence_total,
            "E20": "Evidence Coverage",
            "F20": (
                metrics.evidence_coverage_percent
                / 100
            ),
            "E21": "Orphaned Evidence",
            "F21": metrics.orphaned_evidence,
            "E22": "Duplicate Evidence",
            "F22": metrics.duplicate_evidence,
            "H19": "Open POA&M Items",
            "I19": metrics.poam_total,
            "H20": "POA&M Created",
            "I20": metrics.poam_created,
            "H21": "POA&M Updated",
            "I21": metrics.poam_updated,
            "H22": "POA&M Cleared",
            "I22": metrics.poam_cleared,
            "H23": "Certification Readiness",
            "I23": (
                metrics.certification_readiness_percent
                / 100
            ),
        }

        for cell_reference, value in values.items():
            dashboard_sheet[
                cell_reference
            ] = value

        dashboard_sheet[
            "C24"
        ].number_format = "0.00%"

        dashboard_sheet[
            "F20"
        ].number_format = "0.00%"

        dashboard_sheet[
            "I23"
        ].number_format = "0.00%"

    @staticmethod
    def _configure_recalculation(
        workbook: Workbook,
    ) -> None:
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.calculation.calcMode = "auto"