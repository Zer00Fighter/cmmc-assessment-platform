from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.assessment.assessment_models import (
    Assessment,
    AssessmentMetadata,
    EvidenceReference,
    EvidenceStatus,
    ObjectiveAssessment,
    ObjectiveFinding,
    POAMStatus,
    RequirementAssessmentRecord,
)
from src.scoring import (
    AssessmentFinding,
    AssessmentScore,
    PartialImplementationState,
    RequirementAssessment,
    ScoringEngine,
    ScoringEngineError,
)


class AssessmentEngineError(ValueError):
    """Raised when assessment workflow operations are invalid."""


class AssessmentEngine:
    """
    Manage the complete CMMC Level 2 assessment workflow.

    The engine creates assessments from the compiled control library,
    manages requirement and objective findings, links evidence, applies
    POA&M logic, and delegates score calculation to ScoringEngine.
    """

    def __init__(
        self,
        controls_csv: Path,
        objectives_csv: Path,
        scoring_weights_csv: Path,
    ) -> None:
        self.controls_csv = controls_csv.resolve()
        self.objectives_csv = objectives_csv.resolve()

        self.scoring_engine = ScoringEngine(
            scoring_weights_csv=scoring_weights_csv
        )

        self.control_ids = self._load_control_ids()
        self.objectives_by_requirement = self._load_objectives()

        self._validate_source_data()

    def create_assessment(
        self,
        metadata: AssessmentMetadata,
    ) -> Assessment:
        requirements: Dict[
            str,
            RequirementAssessmentRecord,
        ] = {}

        for requirement_id in self.control_ids:
            objective_assessments = [
                ObjectiveAssessment(
                    requirement_id=requirement_id,
                    objective_id=objective_id,
                )
                for objective_id in self.objectives_by_requirement.get(
                    requirement_id,
                    [],
                )
            ]

            scoring_rule = self.scoring_engine.get_rule(
                requirement_id
            )

            implementation_state = (
                PartialImplementationState.NOT_ASSESSED
                if scoring_rule.partial_credit_allowed
                else None
            )

            requirements[requirement_id] = (
                RequirementAssessmentRecord(
                    requirement_id=requirement_id,
                    implementation_state=implementation_state,
                    objective_assessments=objective_assessments,
                )
            )

        return Assessment(
            metadata=metadata,
            requirements=requirements,
        )

    def update_requirement(
        self,
        assessment: Assessment,
        requirement_id: str,
        *,
        finding: AssessmentFinding | str,
        implementation_state: (
            PartialImplementationState
            | str
            | None
        ) = None,
        applicable: bool = True,
        evidence_status: (
            EvidenceStatus | str
        ) = EvidenceStatus.NOT_STARTED,
        control_owner: str = "",
        assessor: str = "",
        assessment_date: Optional[date] = None,
        ssp_reference: str = "",
        policy_reference: str = "",
        procedure_reference: str = "",
        assessor_notes: str = "",
        management_response: str = "",
    ) -> RequirementAssessmentRecord:
        record = assessment.get_requirement(
            requirement_id
        )

        normalized_finding = self._coerce_finding(
            finding
        )

        normalized_state = self._coerce_optional_state(
            implementation_state
        )

        normalized_evidence_status = (
            self._coerce_evidence_status(
                evidence_status
            )
        )

        scoring_input = RequirementAssessment(
            requirement_id=record.requirement_id,
            finding=normalized_finding,
            implementation_state=normalized_state,
            applicable=applicable,
            notes=assessor_notes,
        )

        try:
            self.scoring_engine.score_requirement(
                scoring_input
            )
        except ScoringEngineError as error:
            raise AssessmentEngineError(
                str(error)
            ) from error

        record.finding = normalized_finding
        record.implementation_state = normalized_state
        record.applicable = applicable
        record.evidence_status = normalized_evidence_status
        record.control_owner = control_owner
        record.assessor = assessor
        record.assessment_date = assessment_date
        record.ssp_reference = ssp_reference
        record.policy_reference = policy_reference
        record.procedure_reference = procedure_reference
        record.assessor_notes = assessor_notes
        record.management_response = management_response

        self._apply_poam_status(record)

        return record

    def update_objective(
        self,
        assessment: Assessment,
        requirement_id: str,
        objective_id: str,
        *,
        finding: ObjectiveFinding | str,
        assessor_notes: str = "",
        evidence_ids: Optional[List[str]] = None,
    ) -> ObjectiveAssessment:
        record = assessment.get_requirement(
            requirement_id
        )

        normalized_objective_id = (
            objective_id.strip().lower()
        )

        objective = next(
            (
                item
                for item in record.objective_assessments
                if item.objective_id
                == normalized_objective_id
            ),
            None,
        )

        if objective is None:
            raise AssessmentEngineError(
                f"Objective {normalized_objective_id} "
                f"does not exist for "
                f"{record.requirement_id}."
            )

        normalized_finding = (
            self._coerce_objective_finding(
                finding
            )
        )

        validated_evidence_ids = (
            self._validate_evidence_ids(
                assessment,
                evidence_ids or [],
            )
        )

        objective.finding = normalized_finding
        objective.assessor_notes = assessor_notes
        objective.evidence_ids = (
            validated_evidence_ids
        )

        return objective

    def add_evidence(
        self,
        assessment: Assessment,
        evidence: EvidenceReference,
    ) -> None:
        assessment.add_evidence(evidence)

    def link_evidence_to_requirement(
        self,
        assessment: Assessment,
        requirement_id: str,
        evidence_ids: Iterable[str],
    ) -> None:
        record = assessment.get_requirement(
            requirement_id
        )

        record.evidence_ids = (
            self._validate_evidence_ids(
                assessment,
                list(evidence_ids),
            )
        )

        if record.evidence_ids:
            record.evidence_status = (
                EvidenceStatus.IN_PROGRESS
            )

    def calculate_score(
        self,
        assessment: Assessment,
    ) -> AssessmentScore:
        scoring_inputs = [
            RequirementAssessment(
                requirement_id=record.requirement_id,
                finding=record.finding,
                implementation_state=(
                    record.implementation_state
                ),
                applicable=record.applicable,
                notes=record.assessor_notes,
            )
            for record in assessment.requirements.values()
        ]

        try:
            return self.scoring_engine.calculate(
                scoring_inputs
            )
        except ScoringEngineError as error:
            raise AssessmentEngineError(
                str(error)
            ) from error

    def synchronize_requirement_from_objectives(
        self,
        assessment: Assessment,
        requirement_id: str,
    ) -> RequirementAssessmentRecord:
        record = assessment.get_requirement(
            requirement_id
        )

        if not record.objective_assessments:
            raise AssessmentEngineError(
                f"{record.requirement_id} has no "
                "assessment objectives."
            )

        if any(
            objective.finding
            == ObjectiveFinding.NOT_ASSESSED
            for objective in record.objective_assessments
        ):
            record.finding = (
                AssessmentFinding.NOT_ASSESSED
            )

        elif all(
            objective.finding
            in {
                ObjectiveFinding.SATISFIED,
                ObjectiveFinding.NOT_APPLICABLE,
            }
            for objective in record.objective_assessments
        ):
            record.finding = AssessmentFinding.MET

        else:
            record.finding = AssessmentFinding.NOT_MET

        scoring_rule = self.scoring_engine.get_rule(
            record.requirement_id
        )

        if scoring_rule.partial_credit_allowed:
            if record.finding == AssessmentFinding.MET:
                record.implementation_state = (
                    PartialImplementationState.FULLY_IMPLEMENTED
                )
            elif (
                record.finding
                == AssessmentFinding.NOT_ASSESSED
            ):
                record.implementation_state = (
                    PartialImplementationState.NOT_ASSESSED
                )

        self._apply_poam_status(record)

        return record

    @staticmethod
    def _apply_poam_status(
        record: RequirementAssessmentRecord,
    ) -> None:
        if record.finding == AssessmentFinding.NOT_MET:
            if record.poam_status in {
                POAMStatus.NOT_REQUIRED,
                POAMStatus.CLOSED,
            }:
                record.poam_status = POAMStatus.OPEN
        else:
            record.poam_status = (
                POAMStatus.NOT_REQUIRED
            )
            record.poam_id = ""

    def _load_control_ids(self) -> List[str]:
        if not self.controls_csv.exists():
            raise FileNotFoundError(
                f"Controls CSV not found: "
                f"{self.controls_csv}"
            )

        with self.controls_csv.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise AssessmentEngineError(
                    "Controls CSV has no header."
                )

            if "requirement_id" not in reader.fieldnames:
                raise AssessmentEngineError(
                    "Controls CSV is missing the "
                    "requirement_id column."
                )

            rows = list(reader)

        return [
            row["requirement_id"]
            .strip()
            .upper()
            for row in rows
            if row.get("requirement_id", "").strip()
        ]

    def _load_objectives(
        self,
    ) -> Dict[str, List[str]]:
        if not self.objectives_csv.exists():
            raise FileNotFoundError(
                f"Objectives CSV not found: "
                f"{self.objectives_csv}"
            )

        with self.objectives_csv.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise AssessmentEngineError(
                    "Objectives CSV has no header."
                )

            required_columns = {
                "requirement_id",
                "objective_id",
            }

            missing_columns = (
                required_columns
                - set(reader.fieldnames)
            )

            if missing_columns:
                raise AssessmentEngineError(
                    "Objectives CSV is missing columns: "
                    + ", ".join(
                        sorted(missing_columns)
                    )
                )

            rows = list(reader)

        objectives: Dict[str, List[str]] = {}

        for row in rows:
            requirement_id = (
                row["requirement_id"]
                .strip()
                .upper()
            )

            objective_id = (
                row["objective_id"]
                .strip()
                .lower()
            )

            if not requirement_id or not objective_id:
                continue

            objectives.setdefault(
                requirement_id,
                [],
            )

            if (
                objective_id
                not in objectives[requirement_id]
            ):
                objectives[requirement_id].append(
                    objective_id
                )

        return objectives

    def _validate_source_data(self) -> None:
        if len(self.control_ids) != 110:
            raise AssessmentEngineError(
                "Assessment Engine expected 110 "
                f"requirements, but found "
                f"{len(self.control_ids)}."
            )

        if len(self.control_ids) != len(
            set(self.control_ids)
        ):
            raise AssessmentEngineError(
                "Duplicate requirement IDs found "
                "in controls data."
            )

        missing_objectives = [
            requirement_id
            for requirement_id in self.control_ids
            if not self.objectives_by_requirement.get(
                requirement_id
            )
        ]

        if missing_objectives:
            raise AssessmentEngineError(
                "Requirements missing objectives: "
                + ", ".join(
                    missing_objectives
                )
            )

        missing_scoring_rules = (
            set(self.control_ids)
            - set(self.scoring_engine.rules)
        )

        if missing_scoring_rules:
            raise AssessmentEngineError(
                "Requirements missing scoring rules: "
                + ", ".join(
                    sorted(missing_scoring_rules)
                )
            )

        unexpected_scoring_rules = (
            set(self.scoring_engine.rules)
            - set(self.control_ids)
        )

        if unexpected_scoring_rules:
            raise AssessmentEngineError(
                "Scoring rules do not match controls: "
                + ", ".join(
                    sorted(
                        unexpected_scoring_rules
                    )
                )
            )

    @staticmethod
    def _validate_evidence_ids(
        assessment: Assessment,
        evidence_ids: List[str],
    ) -> List[str]:
        normalized_ids: List[str] = []

        for evidence_id in evidence_ids:
            normalized_id = evidence_id.strip()

            if not normalized_id:
                continue

            if normalized_id not in (
                assessment.evidence_register
            ):
                raise AssessmentEngineError(
                    f"Unknown evidence ID: "
                    f"{normalized_id}"
                )

            if normalized_id not in normalized_ids:
                normalized_ids.append(
                    normalized_id
                )

        return normalized_ids

    @staticmethod
    def _coerce_finding(
        value: AssessmentFinding | str,
    ) -> AssessmentFinding:
        if isinstance(
            value,
            AssessmentFinding,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            finding.value: finding
            for finding in AssessmentFinding
        }

        aliases["N/A"] = (
            AssessmentFinding.NOT_APPLICABLE
        )
        aliases["NA"] = (
            AssessmentFinding.NOT_APPLICABLE
        )

        try:
            return aliases[normalized]
        except KeyError as error:
            raise AssessmentEngineError(
                f"Unsupported requirement finding: "
                f"{value}"
            ) from error

    @staticmethod
    def _coerce_optional_state(
        value: (
            PartialImplementationState
            | str
            | None
        ),
    ) -> Optional[
        PartialImplementationState
    ]:
        if value is None:
            return None

        if isinstance(
            value,
            PartialImplementationState,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            state.value: state
            for state in (
                PartialImplementationState
            )
        }

        aliases["PARTIAL"] = (
            PartialImplementationState.PARTIALLY_IMPLEMENTED
        )

        aliases["N/A"] = (
            PartialImplementationState.NOT_APPLICABLE
        )

        aliases["NA"] = (
            PartialImplementationState.NOT_APPLICABLE
        )

        try:
            return aliases[normalized]
        except KeyError as error:
            raise AssessmentEngineError(
                "Unsupported implementation state: "
                f"{value}"
            ) from error

    @staticmethod
    def _coerce_evidence_status(
        value: EvidenceStatus | str,
    ) -> EvidenceStatus:
        if isinstance(value, EvidenceStatus):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            status.value: status
            for status in EvidenceStatus
        }

        try:
            return aliases[normalized]
        except KeyError as error:
            raise AssessmentEngineError(
                f"Unsupported evidence status: "
                f"{value}"
            ) from error

    @staticmethod
    def _coerce_objective_finding(
        value: ObjectiveFinding | str,
    ) -> ObjectiveFinding:
        if isinstance(
            value,
            ObjectiveFinding,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("_", " ")
        )

        aliases = {
            finding.value: finding
            for finding in ObjectiveFinding
        }

        aliases["N/A"] = (
            ObjectiveFinding.NOT_APPLICABLE
        )
        aliases["NA"] = (
            ObjectiveFinding.NOT_APPLICABLE
        )

        try:
            return aliases[normalized]
        except KeyError as error:
            raise AssessmentEngineError(
                f"Unsupported objective finding: "
                f"{value}"
            ) from error