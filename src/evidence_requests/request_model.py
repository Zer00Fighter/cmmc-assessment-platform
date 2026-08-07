from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Iterable, List, Optional, Sequence


class EvidenceRequestModelError(ValueError):
    """Raised when an evidence request model is invalid."""


class EvidenceRequestStatus(str, Enum):
    """Lifecycle status for an evidence request."""

    NOT_REQUESTED = "Not Requested"
    REQUESTED = "Requested"
    PENDING_CLIENT = "Pending Client"
    RECEIVED = "Received"
    IN_REVIEW = "In Review"
    ACCEPTED = "Accepted"
    REJECTED_REPLACE = "Rejected / Replace"
    NOT_APPLICABLE = "Not Applicable"
    OVERDUE = "Overdue"


class EvidenceRequestPriority(str, Enum):
    """Priority assigned to an evidence request."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvidenceRequestType(str, Enum):
    """Primary type of evidence being requested."""

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    PLAN = "Plan"
    STANDARD = "Standard"
    CONFIGURATION = "Configuration"
    SCREENSHOT = "Screenshot"
    LOG = "Log"
    REPORT = "Report"
    RECORD = "Record"
    INVENTORY = "Inventory"
    DIAGRAM = "Diagram"
    CONTRACT = "Contract"
    INTERVIEW = "Interview"
    DEMONSTRATION = "Demonstration"
    TEST_RESULT = "Test Result"
    TECHNICAL_EVIDENCE = "Technical Evidence"
    GOVERNANCE_DOCUMENT = "Governance Document"
    OTHER = "Other"


class EvidenceRequestCategory(str, Enum):
    """
    Broad evidence grouping.

    These groupings intentionally align with the SSP supporting-artifact
    concepts we will use later.
    """

    SYSTEM_DESIGN = "System Design Documentation"

    SYSTEM_CONFIGURATION = (
        "System Configuration Settings "
        "and Associated Documentation"
    )

    SUPPLEMENTAL = "Supplemental Artifacts"

    INTERVIEW = "Interview / Demonstration"

    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class ControlReference:
    """
    Reference from an evidence request to a control or requirement.

    The model is framework-neutral. For example:

        framework_id = "CMMC_L2"
        control_id = "AC.L2-3.1.1"

    or:

        framework_id = "HIPAA"
        control_id = "164.312(a)(1)"
    """

    framework_id: str
    control_id: str
    control_title: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        control_id = self.control_id.strip()
        control_title = self.control_title.strip()

        if not framework_id:
            raise EvidenceRequestModelError(
                "ControlReference.framework_id cannot be blank."
            )

        if not control_id:
            raise EvidenceRequestModelError(
                "ControlReference.control_id cannot be blank."
            )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        object.__setattr__(
            self,
            "control_id",
            control_id,
        )

        object.__setattr__(
            self,
            "control_title",
            control_title,
        )


@dataclass(frozen=True, slots=True)
class ObjectiveReference:
    """
    Assessment objective or test-procedure reference.

    Examples:

        control_id = "AC.L2-3.1.1"
        objective_id = "a"

    or for another framework:

        control_id = "PCI-8.3.1"
        objective_id = "8.3.1.a"
    """

    framework_id: str
    control_id: str
    objective_id: str
    objective_text: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        control_id = self.control_id.strip()
        objective_id = self.objective_id.strip()
        objective_text = self.objective_text.strip()

        if not framework_id:
            raise EvidenceRequestModelError(
                "ObjectiveReference.framework_id "
                "cannot be blank."
            )

        if not control_id:
            raise EvidenceRequestModelError(
                "ObjectiveReference.control_id "
                "cannot be blank."
            )

        if not objective_id:
            raise EvidenceRequestModelError(
                "ObjectiveReference.objective_id "
                "cannot be blank."
            )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        object.__setattr__(
            self,
            "control_id",
            control_id,
        )

        object.__setattr__(
            self,
            "objective_id",
            objective_id,
        )

        object.__setattr__(
            self,
            "objective_text",
            objective_text,
        )


@dataclass(frozen=True, slots=True)
class EvidenceGuidance:
    """
    Detailed guidance describing what should be provided.

    An evidence request may include multiple guidance items because one
    logical request can ask for policy, technical, operational, or other
    corroborating evidence.
    """

    evidence_type: EvidenceRequestType
    description: str
    example_artifacts: Sequence[str] = field(
        default_factory=tuple
    )
    required: bool = True

    def __post_init__(self) -> None:
        description = self.description.strip()

        if not description:
            raise EvidenceRequestModelError(
                "EvidenceGuidance.description cannot be blank."
            )

        examples = tuple(
            item.strip()
            for item in self.example_artifacts
            if item and item.strip()
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "example_artifacts",
            examples,
        )


@dataclass(slots=True)
class EvidenceRequest:
    """
    One client-facing documentation / evidence request.

    This is the central model used by:

        request_catalog.py
        request_generator.py
        request_deduplicator.py
        drl_exporter.py
        evidence-register synchronization
        SSP supporting-artifact mapping
    """

    request_id: str

    title: str

    description: str

    category: EvidenceRequestCategory

    evidence_type: EvidenceRequestType

    primary_control: ControlReference

    related_controls: List[ControlReference] = field(
        default_factory=list
    )

    objectives: List[ObjectiveReference] = field(
        default_factory=list
    )

    guidance: List[EvidenceGuidance] = field(
        default_factory=list
    )

    control_owner: str = ""

    client_poc: str = ""

    priority: EvidenceRequestPriority = (
        EvidenceRequestPriority.MEDIUM
    )

    status: EvidenceRequestStatus = (
        EvidenceRequestStatus.NOT_REQUESTED
    )

    requested_date: Optional[date] = None

    due_date: Optional[date] = None

    received_date: Optional[date] = None

    accepted_date: Optional[date] = None

    assessor_notes: str = ""

    source_reference: str = ""

    sprs_weight: Optional[int] = None

    tags: List[str] = field(
        default_factory=list
    )

    generated: bool = True

    def __post_init__(self) -> None:
        self.request_id = self.request_id.strip()
        self.title = self.title.strip()
        self.description = self.description.strip()

        self.control_owner = (
            self.control_owner.strip()
        )

        self.client_poc = (
            self.client_poc.strip()
        )

        self.assessor_notes = (
            self.assessor_notes.strip()
        )

        self.source_reference = (
            self.source_reference.strip()
        )

        self.related_controls = (
            self._deduplicate_controls(
                self.related_controls
            )
        )

        self.objectives = (
            self._deduplicate_objectives(
                self.objectives
            )
        )

        self.guidance = list(
            self.guidance
        )

        self.tags = self._normalize_tags(
            self.tags
        )

        self._validate()

    def _validate(self) -> None:
        if not self.request_id:
            raise EvidenceRequestModelError(
                "EvidenceRequest.request_id cannot be blank."
            )

        if not self.title:
            raise EvidenceRequestModelError(
                "EvidenceRequest.title cannot be blank."
            )

        if not self.description:
            raise EvidenceRequestModelError(
                "EvidenceRequest.description cannot be blank."
            )

        if self.sprs_weight is not None:
            if self.sprs_weight < 0:
                raise EvidenceRequestModelError(
                    "sprs_weight cannot be negative."
                )

        if (
            self.received_date is not None
            and self.requested_date is not None
            and self.received_date < self.requested_date
        ):
            raise EvidenceRequestModelError(
                "received_date cannot be before "
                "requested_date."
            )

        if (
            self.accepted_date is not None
            and self.received_date is not None
            and self.accepted_date < self.received_date
        ):
            raise EvidenceRequestModelError(
                "accepted_date cannot be before "
                "received_date."
            )

    @property
    def all_controls(self) -> List[ControlReference]:
        """
        Primary control followed by related controls.

        Duplicate control references are removed.
        """

        return self._deduplicate_controls(
            [
                self.primary_control,
                *self.related_controls,
            ]
        )

    @property
    def control_ids(self) -> List[str]:
        return [
            control.control_id
            for control in self.all_controls
        ]

    @property
    def objective_ids(self) -> List[str]:
        return [
            objective.objective_id
            for objective in self.objectives
        ]

    @property
    def is_received(self) -> bool:
        return self.status in {
            EvidenceRequestStatus.RECEIVED,
            EvidenceRequestStatus.IN_REVIEW,
            EvidenceRequestStatus.ACCEPTED,
        }

    @property
    def is_accepted(self) -> bool:
        return (
            self.status
            == EvidenceRequestStatus.ACCEPTED
        )

    @property
    def is_open(self) -> bool:
        return self.status in {
            EvidenceRequestStatus.NOT_REQUESTED,
            EvidenceRequestStatus.REQUESTED,
            EvidenceRequestStatus.PENDING_CLIENT,
            EvidenceRequestStatus.RECEIVED,
            EvidenceRequestStatus.IN_REVIEW,
            EvidenceRequestStatus.REJECTED_REPLACE,
            EvidenceRequestStatus.OVERDUE,
        }

    @property
    def is_overdue(self) -> bool:
        if self.status in {
            EvidenceRequestStatus.ACCEPTED,
            EvidenceRequestStatus.NOT_APPLICABLE,
        }:
            return False

        if self.due_date is None:
            return False

        return (
            self.due_date < date.today()
        )

    @property
    def related_control_count(self) -> int:
        return len(
            self.related_controls
        )

    @property
    def coverage_count(self) -> int:
        return len(
            self.all_controls
        )

    def mark_requested(
        self,
        requested_date: Optional[date] = None,
    ) -> None:
        self.requested_date = (
            requested_date
            or date.today()
        )

        self.status = (
            EvidenceRequestStatus.REQUESTED
        )

    def mark_received(
        self,
        received_date: Optional[date] = None,
    ) -> None:
        actual_date = (
            received_date
            or date.today()
        )

        if (
            self.requested_date is not None
            and actual_date < self.requested_date
        ):
            raise EvidenceRequestModelError(
                "received_date cannot be before "
                "requested_date."
            )

        self.received_date = actual_date

        self.status = (
            EvidenceRequestStatus.RECEIVED
        )

    def mark_in_review(self) -> None:
        if self.received_date is None:
            raise EvidenceRequestModelError(
                "An evidence request cannot enter review "
                "before evidence has been received."
            )

        self.status = (
            EvidenceRequestStatus.IN_REVIEW
        )

    def mark_accepted(
        self,
        accepted_date: Optional[date] = None,
    ) -> None:
        if self.received_date is None:
            raise EvidenceRequestModelError(
                "Evidence cannot be accepted before "
                "it has been received."
            )

        actual_date = (
            accepted_date
            or date.today()
        )

        if actual_date < self.received_date:
            raise EvidenceRequestModelError(
                "accepted_date cannot be before "
                "received_date."
            )

        self.accepted_date = actual_date

        self.status = (
            EvidenceRequestStatus.ACCEPTED
        )

    def mark_rejected(
        self,
        notes: str = "",
    ) -> None:
        self.status = (
            EvidenceRequestStatus.REJECTED_REPLACE
        )

        if notes.strip():
            self.assessor_notes = notes.strip()

    def mark_not_applicable(
        self,
        notes: str = "",
    ) -> None:
        self.status = (
            EvidenceRequestStatus.NOT_APPLICABLE
        )

        if notes.strip():
            self.assessor_notes = notes.strip()

    def refresh_overdue_status(
        self,
        as_of: Optional[date] = None,
    ) -> None:
        """
        Convert an open request to OVERDUE when its
        due date has passed.

        Accepted and N/A requests are never marked overdue.
        """

        as_of = as_of or date.today()

        if self.status in {
            EvidenceRequestStatus.ACCEPTED,
            EvidenceRequestStatus.NOT_APPLICABLE,
        }:
            return

        if (
            self.due_date is not None
            and self.due_date < as_of
        ):
            self.status = (
                EvidenceRequestStatus.OVERDUE
            )

    @staticmethod
    def _deduplicate_controls(
        controls: Iterable[ControlReference],
    ) -> List[ControlReference]:
        result: List[ControlReference] = []
        seen = set()

        for control in controls:
            key = (
                control.framework_id.upper(),
                control.control_id.upper(),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(control)

        return result

    @staticmethod
    def _deduplicate_objectives(
        objectives: Iterable[ObjectiveReference],
    ) -> List[ObjectiveReference]:
        result: List[ObjectiveReference] = []
        seen = set()

        for objective in objectives:
            key = (
                objective.framework_id.upper(),
                objective.control_id.upper(),
                objective.objective_id.upper(),
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(objective)

        return result

    @staticmethod
    def _normalize_tags(
        tags: Iterable[str],
    ) -> List[str]:
        result: List[str] = []
        seen = set()

        for tag in tags:
            normalized = tag.strip()

            if not normalized:
                continue

            key = normalized.lower()

            if key in seen:
                continue

            seen.add(key)
            result.append(normalized)

        return result