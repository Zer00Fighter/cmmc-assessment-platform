from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Sequence

from src.scoring import (
    AssessmentFinding,
    PartialImplementationState,
)


class AssessmentStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN PROGRESS"
    READY_FOR_REVIEW = "READY FOR REVIEW"
    FINAL = "FINAL"
    ARCHIVED = "ARCHIVED"


class EvidenceStatus(str, Enum):
    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "IN PROGRESS"
    COMPLETE = "COMPLETE"
    NOT_APPLICABLE = "NOT APPLICABLE"


class ObjectiveFinding(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_SATISFIED = "NOT SATISFIED"
    NOT_APPLICABLE = "NOT APPLICABLE"
    NOT_ASSESSED = "NOT ASSESSED"


class POAMStatus(str, Enum):
    NOT_REQUIRED = "NOT REQUIRED"
    OPEN = "OPEN"
    IN_PROGRESS = "IN PROGRESS"
    COMPLETE = "COMPLETE"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    title: str
    evidence_type: str = ""
    location: str = ""
    owner: str = ""
    reviewed: bool = False
    notes: str = ""


@dataclass
class ObjectiveAssessment:
    requirement_id: str
    objective_id: str
    finding: ObjectiveFinding = ObjectiveFinding.NOT_ASSESSED
    assessor_notes: str = ""
    evidence_ids: List[str] = field(default_factory=list)

    @property
    def assessed(self) -> bool:
        return self.finding != ObjectiveFinding.NOT_ASSESSED

    @property
    def satisfied(self) -> bool:
        return self.finding in {
            ObjectiveFinding.SATISFIED,
            ObjectiveFinding.NOT_APPLICABLE,
        }


@dataclass
class RequirementAssessmentRecord:
    requirement_id: str
    finding: AssessmentFinding = AssessmentFinding.NOT_ASSESSED
    implementation_state: Optional[
        PartialImplementationState
    ] = None
    applicable: bool = True
    evidence_status: EvidenceStatus = EvidenceStatus.NOT_STARTED
    control_owner: str = ""
    assessor: str = ""
    assessment_date: Optional[date] = None
    ssp_reference: str = ""
    policy_reference: str = ""
    procedure_reference: str = ""
    assessor_notes: str = ""
    management_response: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    objective_assessments: List[
        ObjectiveAssessment
    ] = field(default_factory=list)
    poam_status: POAMStatus = POAMStatus.NOT_REQUIRED
    poam_id: str = ""

    @property
    def assessed(self) -> bool:
        return self.finding != AssessmentFinding.NOT_ASSESSED

    @property
    def objective_count(self) -> int:
        return len(self.objective_assessments)

    @property
    def assessed_objective_count(self) -> int:
        return sum(
            objective.assessed
            for objective in self.objective_assessments
        )

    @property
    def satisfied_objective_count(self) -> int:
        return sum(
            objective.satisfied
            for objective in self.objective_assessments
        )

    @property
    def objective_completion_percentage(self) -> float:
        if not self.objective_assessments:
            return 0.0

        return (
            self.assessed_objective_count
            / len(self.objective_assessments)
        )

    @property
    def all_objectives_satisfied(self) -> bool:
        if not self.objective_assessments:
            return False

        return all(
            objective.satisfied
            for objective in self.objective_assessments
        )


@dataclass(frozen=True)
class AssessmentMetadata:
    assessment_id: str
    organization_name: str
    assessment_name: str
    assessment_type: str = "CMMC Level 2 Self-Assessment"
    cage_code: str = ""
    scope: str = ""
    lead_assessor: str = ""
    assessment_start_date: Optional[date] = None
    assessment_end_date: Optional[date] = None
    status: AssessmentStatus = AssessmentStatus.DRAFT
    created_at: datetime = field(
        default_factory=datetime.utcnow
    )
    updated_at: datetime = field(
        default_factory=datetime.utcnow
    )


@dataclass
class Assessment:
    metadata: AssessmentMetadata
    requirements: Dict[
        str,
        RequirementAssessmentRecord,
    ] = field(default_factory=dict)
    evidence_register: Dict[
        str,
        EvidenceReference,
    ] = field(default_factory=dict)

    def get_requirement(
        self,
        requirement_id: str,
    ) -> RequirementAssessmentRecord:
        normalized_id = requirement_id.strip().upper()

        try:
            return self.requirements[normalized_id]
        except KeyError as error:
            raise KeyError(
                f"Requirement not found in assessment: "
                f"{normalized_id}"
            ) from error

    def add_evidence(
        self,
        evidence: EvidenceReference,
    ) -> None:
        evidence_id = evidence.evidence_id.strip()

        if not evidence_id:
            raise ValueError(
                "Evidence ID cannot be empty."
            )

        if evidence_id in self.evidence_register:
            raise ValueError(
                f"Duplicate evidence ID: {evidence_id}"
            )

        self.evidence_register[evidence_id] = evidence

    @property
    def requirement_count(self) -> int:
        return len(self.requirements)

    @property
    def assessed_requirement_count(self) -> int:
        return sum(
            record.assessed
            for record in self.requirements.values()
        )

    @property
    def completion_percentage(self) -> float:
        if not self.requirements:
            return 0.0

        return (
            self.assessed_requirement_count
            / len(self.requirements)
        )

    @property
    def open_poam_count(self) -> int:
        return sum(
            record.poam_status
            in {
                POAMStatus.OPEN,
                POAMStatus.IN_PROGRESS,
            }
            for record in self.requirements.values()
        )

    def requirement_records(
        self,
    ) -> Sequence[RequirementAssessmentRecord]:
        return tuple(self.requirements.values())