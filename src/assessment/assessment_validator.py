from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.assessment.assessment_models import (
    Assessment,
    AssessmentStatus,
    EvidenceStatus,
    ObjectiveFinding,
    POAMStatus,
)
from src.scoring import (
    AssessmentFinding,
    PartialImplementationState,
)
from src.assessment.assessment_engine import (
    AssessmentEngine,
    AssessmentEngineError,
)


class AssessmentValidationError(RuntimeError):
    """Raised when an assessment fails readiness or finalization validation."""


@dataclass(frozen=True)
class AssessmentValidationIssue:
    """One assessment validation error or warning."""

    severity: str
    code: str
    message: str
    requirement_id: str = ""
    objective_id: str = ""
    evidence_id: str = ""


@dataclass
class AssessmentValidationReport:
    """Complete assessment validation result."""

    assessment_id: str
    assessment_status: AssessmentStatus
    requirement_count: int
    assessed_requirement_count: int
    evidence_count: int
    open_poam_count: int
    current_score: int | None = None
    score_complete: bool = False
    errors: List[AssessmentValidationIssue] = field(
        default_factory=list
    )
    warnings: List[AssessmentValidationIssue] = field(
        default_factory=list
    )

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def raise_for_errors(self) -> None:
        if self.passed:
            return

        details = "\n".join(
            self._format_issue(issue)
            for issue in self.errors
        )

        raise AssessmentValidationError(
            "CMMC assessment validation failed:\n"
            f"{details}"
        )

    @staticmethod
    def _format_issue(
        issue: AssessmentValidationIssue,
    ) -> str:
        references: List[str] = []

        if issue.requirement_id:
            references.append(
                f"requirement={issue.requirement_id}"
            )

        if issue.objective_id:
            references.append(
                f"objective={issue.objective_id}"
            )

        if issue.evidence_id:
            references.append(
                f"evidence={issue.evidence_id}"
            )

        reference_text = (
            f" ({', '.join(references)})"
            if references
            else ""
        )

        return (
            f"[{issue.code}] "
            f"{issue.message}"
            f"{reference_text}"
        )


class AssessmentValidator:
    """
    Validate an Assessment before review or finalization.

    Validation modes:

    DRAFT / IN PROGRESS:
        Performs structural and consistency checks. Incomplete assessment
        content generally produces warnings.

    READY FOR REVIEW:
        Requires all requirements to be assessed, valid assessor metadata,
        objective consistency, evidence linkage, and POA&M handling.

    FINAL:
        Applies all Ready-for-Review rules plus stricter evidence,
        assessment-date, POA&M, and score-completeness requirements.
    """

    EXPECTED_REQUIREMENT_COUNT = 110

    def __init__(
        self,
        assessment_engine: AssessmentEngine,
    ) -> None:
        self.assessment_engine = assessment_engine

    def validate(
        self,
        assessment: Assessment,
        *,
        target_status: AssessmentStatus | str | None = None,
    ) -> AssessmentValidationReport:
        resolved_status = self._coerce_status(
            target_status
            if target_status is not None
            else assessment.metadata.status
        )

        report = AssessmentValidationReport(
            assessment_id=(
                assessment.metadata.assessment_id
            ),
            assessment_status=resolved_status,
            requirement_count=(
                assessment.requirement_count
            ),
            assessed_requirement_count=(
                assessment.assessed_requirement_count
            ),
            evidence_count=len(
                assessment.evidence_register
            ),
            open_poam_count=(
                assessment.open_poam_count
            ),
        )

        self._validate_metadata(
            assessment,
            resolved_status,
            report,
        )

        self._validate_requirement_structure(
            assessment,
            report,
        )

        self._validate_requirement_records(
            assessment,
            resolved_status,
            report,
        )

        self._validate_evidence_register(
            assessment,
            report,
        )

        self._validate_score(
            assessment,
            resolved_status,
            report,
        )

        return report

    def validate_or_raise(
        self,
        assessment: Assessment,
        *,
        target_status: AssessmentStatus | str | None = None,
    ) -> AssessmentValidationReport:
        report = self.validate(
            assessment,
            target_status=target_status,
        )

        report.raise_for_errors()
        return report

    def validate_ready_for_review(
        self,
        assessment: Assessment,
    ) -> AssessmentValidationReport:
        return self.validate(
            assessment,
            target_status=(
                AssessmentStatus.READY_FOR_REVIEW
            ),
        )

    def validate_ready_for_review_or_raise(
        self,
        assessment: Assessment,
    ) -> AssessmentValidationReport:
        return self.validate_or_raise(
            assessment,
            target_status=(
                AssessmentStatus.READY_FOR_REVIEW
            ),
        )

    def validate_final(
        self,
        assessment: Assessment,
    ) -> AssessmentValidationReport:
        return self.validate(
            assessment,
            target_status=AssessmentStatus.FINAL,
        )

    def validate_final_or_raise(
        self,
        assessment: Assessment,
    ) -> AssessmentValidationReport:
        return self.validate_or_raise(
            assessment,
            target_status=AssessmentStatus.FINAL,
        )

    def _validate_metadata(
        self,
        assessment: Assessment,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        metadata = assessment.metadata

        if not metadata.assessment_id.strip():
            self._add_error(
                report,
                code="EMPTY_ASSESSMENT_ID",
                message=(
                    "Assessment ID cannot be empty."
                ),
            )

        if not metadata.organization_name.strip():
            self._add_error(
                report,
                code="EMPTY_ORGANIZATION_NAME",
                message=(
                    "Organization name cannot be empty."
                ),
            )

        if not metadata.assessment_name.strip():
            self._add_error(
                report,
                code="EMPTY_ASSESSMENT_NAME",
                message=(
                    "Assessment name cannot be empty."
                ),
            )

        if not metadata.assessment_type.strip():
            self._add_error(
                report,
                code="EMPTY_ASSESSMENT_TYPE",
                message=(
                    "Assessment type cannot be empty."
                ),
            )

        if target_status in {
            AssessmentStatus.READY_FOR_REVIEW,
            AssessmentStatus.FINAL,
        }:
            if not metadata.scope.strip():
                self._add_error(
                    report,
                    code="MISSING_SCOPE",
                    message=(
                        "Assessment scope is required "
                        "before review or finalization."
                    ),
                )

            if not metadata.lead_assessor.strip():
                self._add_error(
                    report,
                    code="MISSING_LEAD_ASSESSOR",
                    message=(
                        "Lead assessor is required "
                        "before review or finalization."
                    ),
                )

            if metadata.assessment_start_date is None:
                self._add_error(
                    report,
                    code="MISSING_START_DATE",
                    message=(
                        "Assessment start date is required "
                        "before review or finalization."
                    ),
                )

        if target_status == AssessmentStatus.FINAL:
            if metadata.assessment_end_date is None:
                self._add_error(
                    report,
                    code="MISSING_END_DATE",
                    message=(
                        "Assessment end date is required "
                        "before finalization."
                    ),
                )

            if (
                metadata.assessment_start_date is not None
                and metadata.assessment_end_date is not None
                and metadata.assessment_end_date
                < metadata.assessment_start_date
            ):
                self._add_error(
                    report,
                    code="INVALID_DATE_RANGE",
                    message=(
                        "Assessment end date cannot occur "
                        "before the start date."
                    ),
                )

        elif (
            metadata.assessment_start_date is not None
            and metadata.assessment_end_date is not None
            and metadata.assessment_end_date
            < metadata.assessment_start_date
        ):
            self._add_warning(
                report,
                code="INVALID_DATE_RANGE",
                message=(
                    "Assessment end date occurs before "
                    "the start date."
                ),
            )

    def _validate_requirement_structure(
        self,
        assessment: Assessment,
        report: AssessmentValidationReport,
    ) -> None:
        if (
            assessment.requirement_count
            != self.EXPECTED_REQUIREMENT_COUNT
        ):
            self._add_error(
                report,
                code="REQUIREMENT_COUNT",
                message=(
                    f"Expected "
                    f"{self.EXPECTED_REQUIREMENT_COUNT} "
                    "requirements, but found "
                    f"{assessment.requirement_count}."
                ),
            )

        expected_ids = set(
            self.assessment_engine.control_ids
        )

        actual_ids = set(
            assessment.requirements
        )

        missing_ids = sorted(
            expected_ids - actual_ids
        )

        unexpected_ids = sorted(
            actual_ids - expected_ids
        )

        for requirement_id in missing_ids:
            self._add_error(
                report,
                code="MISSING_REQUIREMENT",
                message=(
                    "Assessment is missing an official "
                    "CMMC requirement."
                ),
                requirement_id=requirement_id,
            )

        for requirement_id in unexpected_ids:
            self._add_error(
                report,
                code="UNEXPECTED_REQUIREMENT",
                message=(
                    "Assessment contains an unknown "
                    "requirement."
                ),
                requirement_id=requirement_id,
            )

    def _validate_requirement_records(
        self,
        assessment: Assessment,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        for requirement_id, record in (
            assessment.requirements.items()
        ):
            self._validate_requirement_record(
                assessment,
                requirement_id,
                record,
                target_status,
                report,
            )

    def _validate_requirement_record(
        self,
        assessment: Assessment,
        requirement_id: str,
        record,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        if record.requirement_id != requirement_id:
            self._add_error(
                report,
                code="REQUIREMENT_ID_MISMATCH",
                message=(
                    "Requirement dictionary key and "
                    "record ID do not match."
                ),
                requirement_id=requirement_id,
            )

        try:
            scoring_rule = (
                self.assessment_engine
                .scoring_engine
                .get_rule(requirement_id)
            )
        except Exception as error:
            self._add_error(
                report,
                code="MISSING_SCORING_RULE",
                message=str(error),
                requirement_id=requirement_id,
            )
            return

        self._validate_finding_and_applicability(
            record,
            requirement_id,
            report,
        )

        self._validate_partial_credit_state(
            record,
            scoring_rule,
            requirement_id,
            report,
        )

        self._validate_objectives(
            record,
            requirement_id,
            target_status,
            report,
        )

        self._validate_requirement_evidence(
            assessment,
            record,
            requirement_id,
            target_status,
            report,
        )

        self._validate_poam(
            record,
            requirement_id,
            target_status,
            report,
        )

        if target_status in {
            AssessmentStatus.READY_FOR_REVIEW,
            AssessmentStatus.FINAL,
        }:
            if (
                record.finding
                == AssessmentFinding.NOT_ASSESSED
            ):
                self._add_error(
                    report,
                    code="REQUIREMENT_NOT_ASSESSED",
                    message=(
                        "All requirements must have a "
                        "final finding before review."
                    ),
                    requirement_id=requirement_id,
                )

            if not record.assessor.strip():
                self._add_error(
                    report,
                    code="MISSING_REQUIREMENT_ASSESSOR",
                    message=(
                        "An assessor must be recorded "
                        "for each assessed requirement."
                    ),
                    requirement_id=requirement_id,
                )

            if record.assessment_date is None:
                self._add_error(
                    report,
                    code="MISSING_ASSESSMENT_DATE",
                    message=(
                        "An assessment date must be "
                        "recorded for each requirement."
                    ),
                    requirement_id=requirement_id,
                )

        elif record.assessed:
            if not record.assessor.strip():
                self._add_warning(
                    report,
                    code="MISSING_REQUIREMENT_ASSESSOR",
                    message=(
                        "Assessed requirement has no "
                        "recorded assessor."
                    ),
                    requirement_id=requirement_id,
                )

            if record.assessment_date is None:
                self._add_warning(
                    report,
                    code="MISSING_ASSESSMENT_DATE",
                    message=(
                        "Assessed requirement has no "
                        "assessment date."
                    ),
                    requirement_id=requirement_id,
                )

    def _validate_finding_and_applicability(
        self,
        record,
        requirement_id: str,
        report: AssessmentValidationReport,
    ) -> None:
        if not record.applicable:
            if record.finding not in {
                AssessmentFinding.NOT_APPLICABLE,
                AssessmentFinding.NOT_ASSESSED,
            }:
                self._add_error(
                    report,
                    code="NON_APPLICABLE_FINDING",
                    message=(
                        "A non-applicable requirement "
                        "must be NOT APPLICABLE or "
                        "NOT ASSESSED."
                    ),
                    requirement_id=requirement_id,
                )

        if (
            record.finding
            == AssessmentFinding.NOT_APPLICABLE
            and record.applicable
        ):
            self._add_error(
                report,
                code="APPLICABILITY_MISMATCH",
                message=(
                    "Requirement is assessed "
                    "NOT APPLICABLE but remains marked "
                    "as applicable."
                ),
                requirement_id=requirement_id,
            )

    def _validate_partial_credit_state(
        self,
        record,
        scoring_rule,
        requirement_id: str,
        report: AssessmentValidationReport,
    ) -> None:
        state = record.implementation_state

        if scoring_rule.partial_credit_allowed:
            expected_states = {
                AssessmentFinding.MET: {
                    PartialImplementationState.FULLY_IMPLEMENTED,
                },
                AssessmentFinding.NOT_MET: {
                    PartialImplementationState.PARTIALLY_IMPLEMENTED,
                    PartialImplementationState.NOT_IMPLEMENTED,
                },
                AssessmentFinding.NOT_APPLICABLE: {
                    PartialImplementationState.NOT_APPLICABLE,
                },
                AssessmentFinding.NOT_ASSESSED: {
                    PartialImplementationState.NOT_ASSESSED,
                },
            }

            valid_states = expected_states.get(
                record.finding,
                set(),
            )

            if state not in valid_states:
                allowed_values = ", ".join(
                    sorted(
                        item.value
                        for item in valid_states
                    )
                )

                self._add_error(
                    report,
                    code="INVALID_PARTIAL_STATE",
                    message=(
                        f"Finding {record.finding.value} "
                        "requires implementation state: "
                        f"{allowed_values or 'none'}."
                    ),
                    requirement_id=requirement_id,
                )

        elif state not in {
            None,
            PartialImplementationState.NOT_IMPLEMENTED,
        }:
            self._add_error(
                report,
                code="UNEXPECTED_IMPLEMENTATION_STATE",
                message=(
                    "This requirement does not permit "
                    "partial-credit implementation states."
                ),
                requirement_id=requirement_id,
            )

    def _validate_objectives(
        self,
        record,
        requirement_id: str,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        expected_objective_ids = set(
            self.assessment_engine
            .objectives_by_requirement
            .get(requirement_id, [])
        )

        actual_objective_ids = [
            objective.objective_id
            for objective in record.objective_assessments
        ]

        if len(actual_objective_ids) != len(
            set(actual_objective_ids)
        ):
            self._add_error(
                report,
                code="DUPLICATE_OBJECTIVE",
                message=(
                    "Requirement contains duplicate "
                    "objective IDs."
                ),
                requirement_id=requirement_id,
            )

        missing_objectives = sorted(
            expected_objective_ids
            - set(actual_objective_ids)
        )

        unexpected_objectives = sorted(
            set(actual_objective_ids)
            - expected_objective_ids
        )

        for objective_id in missing_objectives:
            self._add_error(
                report,
                code="MISSING_OBJECTIVE",
                message=(
                    "Requirement is missing an official "
                    "assessment objective."
                ),
                requirement_id=requirement_id,
                objective_id=objective_id,
            )

        for objective_id in unexpected_objectives:
            self._add_error(
                report,
                code="UNEXPECTED_OBJECTIVE",
                message=(
                    "Requirement contains an unknown "
                    "assessment objective."
                ),
                requirement_id=requirement_id,
                objective_id=objective_id,
            )

        for objective in record.objective_assessments:
            if (
                objective.requirement_id
                != requirement_id
            ):
                self._add_error(
                    report,
                    code="OBJECTIVE_REQUIREMENT_MISMATCH",
                    message=(
                        "Objective is linked to a different "
                        "requirement ID."
                    ),
                    requirement_id=requirement_id,
                    objective_id=(
                        objective.objective_id
                    ),
                )

            if target_status in {
                AssessmentStatus.READY_FOR_REVIEW,
                AssessmentStatus.FINAL,
            }:
                if (
                    objective.finding
                    == ObjectiveFinding.NOT_ASSESSED
                ):
                    self._add_error(
                        report,
                        code="OBJECTIVE_NOT_ASSESSED",
                        message=(
                            "All objectives must be assessed "
                            "before review or finalization."
                        ),
                        requirement_id=requirement_id,
                        objective_id=(
                            objective.objective_id
                        ),
                    )

        objective_findings = {
            objective.finding
            for objective in record.objective_assessments
        }

        if (
            record.finding == AssessmentFinding.MET
            and any(
                finding
                not in {
                    ObjectiveFinding.SATISFIED,
                    ObjectiveFinding.NOT_APPLICABLE,
                }
                for finding in objective_findings
            )
        ):
            self._add_error(
                report,
                code="MET_OBJECTIVE_MISMATCH",
                message=(
                    "A MET requirement cannot contain "
                    "an unsatisfied or unassessed objective."
                ),
                requirement_id=requirement_id,
            )

        if (
            record.finding == AssessmentFinding.NOT_MET
            and record.objective_assessments
            and all(
                objective.finding
                in {
                    ObjectiveFinding.SATISFIED,
                    ObjectiveFinding.NOT_APPLICABLE,
                }
                for objective in (
                    record.objective_assessments
                )
            )
        ):
            self._add_warning(
                report,
                code="NOT_MET_OBJECTIVE_MISMATCH",
                message=(
                    "Requirement is NOT MET even though "
                    "all objectives appear satisfied."
                ),
                requirement_id=requirement_id,
            )

    def _validate_requirement_evidence(
        self,
        assessment: Assessment,
        record,
        requirement_id: str,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        linked_ids = list(record.evidence_ids)

        if len(linked_ids) != len(set(linked_ids)):
            self._add_warning(
                report,
                code="DUPLICATE_REQUIREMENT_EVIDENCE",
                message=(
                    "Requirement contains duplicate "
                    "evidence links."
                ),
                requirement_id=requirement_id,
            )

        for evidence_id in linked_ids:
            if (
                evidence_id
                not in assessment.evidence_register
            ):
                self._add_error(
                    report,
                    code="UNKNOWN_EVIDENCE",
                    message=(
                        "Requirement links to evidence "
                        "that does not exist."
                    ),
                    requirement_id=requirement_id,
                    evidence_id=evidence_id,
                )

        objective_evidence_ids: List[str] = []

        for objective in record.objective_assessments:
            for evidence_id in objective.evidence_ids:
                objective_evidence_ids.append(
                    evidence_id
                )

                if (
                    evidence_id
                    not in assessment.evidence_register
                ):
                    self._add_error(
                        report,
                        code="UNKNOWN_OBJECTIVE_EVIDENCE",
                        message=(
                            "Objective links to evidence "
                            "that does not exist."
                        ),
                        requirement_id=requirement_id,
                        objective_id=(
                            objective.objective_id
                        ),
                        evidence_id=evidence_id,
                    )

        all_linked_ids = set(
            linked_ids + objective_evidence_ids
        )

        if (
            record.evidence_status
            == EvidenceStatus.COMPLETE
            and not all_linked_ids
        ):
            self._add_error(
                report,
                code="COMPLETE_WITHOUT_EVIDENCE",
                message=(
                    "Evidence status is COMPLETE but no "
                    "evidence is linked."
                ),
                requirement_id=requirement_id,
            )

        if (
            record.evidence_status
            == EvidenceStatus.NOT_APPLICABLE
            and record.finding
            not in {
                AssessmentFinding.NOT_APPLICABLE,
                AssessmentFinding.NOT_ASSESSED,
            }
        ):
            self._add_warning(
                report,
                code="EVIDENCE_NOT_APPLICABLE_MISMATCH",
                message=(
                    "Evidence is marked NOT APPLICABLE "
                    "for an applicable assessed requirement."
                ),
                requirement_id=requirement_id,
            )

        if target_status == AssessmentStatus.FINAL:
            if (
                record.finding
                in {
                    AssessmentFinding.MET,
                    AssessmentFinding.NOT_MET,
                }
                and record.evidence_status
                != EvidenceStatus.COMPLETE
            ):
                self._add_error(
                    report,
                    code="FINAL_EVIDENCE_INCOMPLETE",
                    message=(
                        "Final assessed requirements must "
                        "have COMPLETE evidence status."
                    ),
                    requirement_id=requirement_id,
                )

            for evidence_id in all_linked_ids:
                evidence = (
                    assessment.evidence_register.get(
                        evidence_id
                    )
                )

                if (
                    evidence is not None
                    and not evidence.reviewed
                ):
                    self._add_error(
                        report,
                        code="UNREVIEWED_EVIDENCE",
                        message=(
                            "Evidence linked to a final "
                            "assessment has not been reviewed."
                        ),
                        requirement_id=requirement_id,
                        evidence_id=evidence_id,
                    )

    def _validate_poam(
        self,
        record,
        requirement_id: str,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        if record.finding == AssessmentFinding.NOT_MET:
            if record.poam_status == POAMStatus.NOT_REQUIRED:
                self._add_error(
                    report,
                    code="POAM_REQUIRED",
                    message=(
                        "NOT MET requirement must have an "
                        "active or completed POA&M status."
                    ),
                    requirement_id=requirement_id,
                )

            if target_status in {
                AssessmentStatus.READY_FOR_REVIEW,
                AssessmentStatus.FINAL,
            }:
                if not record.poam_id.strip():
                    self._add_error(
                        report,
                        code="MISSING_POAM_ID",
                        message=(
                            "NOT MET requirement requires "
                            "a POA&M identifier before "
                            "review or finalization."
                        ),
                        requirement_id=requirement_id,
                    )

        elif record.poam_status in {
            POAMStatus.OPEN,
            POAMStatus.IN_PROGRESS,
        }:
            self._add_warning(
                report,
                code="UNEXPECTED_OPEN_POAM",
                message=(
                    "Requirement is not NOT MET but still "
                    "has an open POA&M."
                ),
                requirement_id=requirement_id,
            )

        if (
            target_status == AssessmentStatus.FINAL
            and record.poam_status
            in {
                POAMStatus.OPEN,
                POAMStatus.IN_PROGRESS,
            }
        ):
            self._add_warning(
                report,
                code="FINAL_WITH_OPEN_POAM",
                message=(
                    "Final assessment contains an open "
                    "POA&M item."
                ),
                requirement_id=requirement_id,
            )

    def _validate_evidence_register(
        self,
        assessment: Assessment,
        report: AssessmentValidationReport,
    ) -> None:
        for evidence_id, evidence in (
            assessment.evidence_register.items()
        ):
            if not evidence_id.strip():
                self._add_error(
                    report,
                    code="EMPTY_EVIDENCE_ID",
                    message=(
                        "Evidence register contains an "
                        "empty evidence ID."
                    ),
                )

            if (
                evidence.evidence_id.strip()
                != evidence_id
            ):
                self._add_error(
                    report,
                    code="EVIDENCE_ID_MISMATCH",
                    message=(
                        "Evidence dictionary key and "
                        "evidence record ID do not match."
                    ),
                    evidence_id=evidence_id,
                )

            if not evidence.title.strip():
                self._add_error(
                    report,
                    code="EMPTY_EVIDENCE_TITLE",
                    message=(
                        "Evidence record has no title."
                    ),
                    evidence_id=evidence_id,
                )

            if not evidence.location.strip():
                self._add_warning(
                    report,
                    code="MISSING_EVIDENCE_LOCATION",
                    message=(
                        "Evidence record has no storage "
                        "location or reference."
                    ),
                    evidence_id=evidence_id,
                )

    def _validate_score(
        self,
        assessment: Assessment,
        target_status: AssessmentStatus,
        report: AssessmentValidationReport,
    ) -> None:
        try:
            score = (
                self.assessment_engine
                .calculate_score(assessment)
            )
        except AssessmentEngineError as error:
            self._add_error(
                report,
                code="SCORING_FAILURE",
                message=str(error),
            )
            return

        report.current_score = (
            score.current_score
        )
        report.score_complete = score.complete

        if target_status in {
            AssessmentStatus.READY_FOR_REVIEW,
            AssessmentStatus.FINAL,
        }:
            if not score.complete:
                self._add_error(
                    report,
                    code="INCOMPLETE_SCORE",
                    message=(
                        "Assessment score is incomplete "
                        "because one or more requirements "
                        "remain NOT ASSESSED."
                    ),
                )

        elif not score.complete:
            self._add_warning(
                report,
                code="PROVISIONAL_SCORE",
                message=(
                    "Current score is provisional because "
                    "one or more requirements remain "
                    "NOT ASSESSED."
                ),
            )

    @staticmethod
    def _coerce_status(
        value: AssessmentStatus | str,
    ) -> AssessmentStatus:
        if isinstance(value, AssessmentStatus):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            status.value: status
            for status in AssessmentStatus
        }

        try:
            return aliases[normalized]
        except KeyError as error:
            raise AssessmentValidationError(
                f"Unsupported assessment status: "
                f"{value}"
            ) from error

    @staticmethod
    def _add_error(
        report: AssessmentValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
        objective_id: str = "",
        evidence_id: str = "",
    ) -> None:
        report.errors.append(
            AssessmentValidationIssue(
                severity="ERROR",
                code=code,
                message=message,
                requirement_id=requirement_id,
                objective_id=objective_id,
                evidence_id=evidence_id,
            )
        )

    @staticmethod
    def _add_warning(
        report: AssessmentValidationReport,
        code: str,
        message: str,
        requirement_id: str = "",
        objective_id: str = "",
        evidence_id: str = "",
    ) -> None:
        report.warnings.append(
            AssessmentValidationIssue(
                severity="WARNING",
                code=code,
                message=message,
                requirement_id=requirement_id,
                objective_id=objective_id,
                evidence_id=evidence_id,
            )
        )