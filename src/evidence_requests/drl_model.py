from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Iterable, List, Optional, Sequence, Tuple


class DRLModelError(ValueError):
    """Raised when Documentation Request List data is invalid."""


class DocumentationRequestStatus(str, Enum):
    """
    Client-facing submission status.

    The DRL intentionally does not contain detailed assessor evidence
    sufficiency or assessment-result states. Those belong in the
    Evidence Register.
    """

    NOT_REQUESTED = "Not Requested"
    REQUESTED = "Requested"
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    ACCEPTED = "Accepted"
    NEEDS_REVISION = "Needs Revision"
    NOT_APPLICABLE = "Not Applicable"


class DocumentationRequestPriority(str, Enum):
    """Client-facing request priority."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DocumentationRequestType(str, Enum):
    """Type of documentation or evidence requested."""

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    PLAN = "Plan"
    SYSTEM_SECURITY_PLAN = "System Security Plan"
    STANDARD = "Standard"
    CONFIGURATION = "Configuration"
    CONFIGURATION_BASELINE = "Configuration Baseline"
    SCREENSHOT = "Screenshot"
    LOG = "Log"
    REPORT = "Report"
    RECORD = "Record"
    INVENTORY = "Inventory"
    DIAGRAM = "Diagram"
    CONTRACT = "Contract"
    AGREEMENT = "Agreement"
    INTERCONNECTION = "Interconnection"
    PERSONNEL_RECORD = "Personnel Record"
    TRAINING_RECORD = "Training Record"
    RISK_ASSESSMENT = "Risk Assessment"
    SECURITY_ASSESSMENT = "Security Assessment"
    POAM = "POA&M"
    INTERVIEW = "Interview"
    DEMONSTRATION = "Demonstration"
    TEST_RESULT = "Test Result"
    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class DocumentationRequestControl:
    """
    Framework/control mapping shown in the DRL.

    The DRL can initially be generated for CMMC but remains capable
    of representing other frameworks later.
    """

    framework_id: str
    control_id: str
    family: str = ""
    control_title: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        control_id = self.control_id.strip()
        family = self.family.strip()
        control_title = self.control_title.strip()

        if not framework_id:
            raise DRLModelError(
                "DocumentationRequestControl.framework_id "
                "cannot be blank."
            )

        if not control_id:
            raise DRLModelError(
                "DocumentationRequestControl.control_id "
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
            "family",
            family,
        )

        object.__setattr__(
            self,
            "control_title",
            control_title,
        )

    @property
    def key(self) -> Tuple[str, str]:
        return (
            self.framework_id.casefold(),
            self.control_id.casefold(),
        )


@dataclass(slots=True)
class DocumentationRequest:
    """
    One client-facing Documentation Request List entry.

    Fields intentionally focus on:
      - what is being requested;
      - why it is being requested;
      - what controls it supports;
      - submission tracking;
      - high-level assessor review tracking.

    Detailed evidence evaluation belongs in the Evidence Register.
    """

    request_id: str

    requested_item: str

    evidence_type: DocumentationRequestType

    priority: DocumentationRequestPriority

    controls: List[
        DocumentationRequestControl
    ] = field(
        default_factory=list
    )

    description: str = ""

    submitted: bool = False

    date_submitted: Optional[date] = None

    current_version: str = ""

    file_name: str = ""

    evidence_location: str = ""

    review_status: DocumentationRequestStatus = (
        DocumentationRequestStatus.NOT_REQUESTED
    )

    date_reviewed: Optional[date] = None

    reviewer: str = ""

    comments: str = ""

    client_poc: str = ""

    due_date: Optional[date] = None

    generated: bool = True

    def __post_init__(self) -> None:
        self.request_id = self.request_id.strip()
        self.requested_item = self.requested_item.strip()
        self.description = self.description.strip()
        self.current_version = self.current_version.strip()
        self.file_name = self.file_name.strip()
        self.evidence_location = self.evidence_location.strip()
        self.reviewer = self.reviewer.strip()
        self.comments = self.comments.strip()
        self.client_poc = self.client_poc.strip()

        if not self.request_id:
            raise DRLModelError(
                "DocumentationRequest.request_id "
                "cannot be blank."
            )

        if not self.requested_item:
            raise DRLModelError(
                "DocumentationRequest.requested_item "
                "cannot be blank."
            )

        self.controls = self._deduplicate_controls(
            self.controls
        )

        self._validate_dates()

    def _validate_dates(self) -> None:
        if (
            self.date_reviewed is not None
            and self.date_submitted is not None
            and self.date_reviewed < self.date_submitted
        ):
            raise DRLModelError(
                "date_reviewed cannot be before "
                "date_submitted."
            )

    @property
    def control_ids(self) -> Tuple[str, ...]:
        return tuple(
            control.control_id
            for control in self.controls
        )

    @property
    def framework_ids(self) -> Tuple[str, ...]:
        values: List[str] = []
        seen = set()

        for control in self.controls:
            key = control.framework_id.casefold()

            if key in seen:
                continue

            seen.add(key)
            values.append(
                control.framework_id
            )

        return tuple(values)

    @property
    def control_families(self) -> Tuple[str, ...]:
        values: List[str] = []
        seen = set()

        for control in self.controls:
            family = control.family.strip()

            if not family:
                continue

            key = family.casefold()

            if key in seen:
                continue

            seen.add(key)
            values.append(family)

        return tuple(values)

    @property
    def reuse_count(self) -> int:
        """
        Number of unique controls supported by this request.
        """

        return len(self.controls)

    @property
    def is_reused(self) -> bool:
        return self.reuse_count > 1

    @property
    def is_complete(self) -> bool:
        return (
            self.review_status
            == DocumentationRequestStatus.ACCEPTED
        )

    @property
    def needs_client_action(self) -> bool:
        return self.review_status in {
            DocumentationRequestStatus.NOT_REQUESTED,
            DocumentationRequestStatus.REQUESTED,
            DocumentationRequestStatus.PENDING,
            DocumentationRequestStatus.NEEDS_REVISION,
        }

    @property
    def is_overdue(self) -> bool:
        if self.due_date is None:
            return False

        if self.review_status in {
            DocumentationRequestStatus.ACCEPTED,
            DocumentationRequestStatus.NOT_APPLICABLE,
        }:
            return False

        return self.due_date < date.today()

    def mark_requested(self) -> None:
        self.review_status = (
            DocumentationRequestStatus.REQUESTED
        )

    def mark_submitted(
        self,
        *,
        submitted_date: Optional[date] = None,
        file_name: str = "",
        location: str = "",
        version: str = "",
    ) -> None:
        self.submitted = True

        self.date_submitted = (
            submitted_date
            or date.today()
        )

        if file_name.strip():
            self.file_name = file_name.strip()

        if location.strip():
            self.evidence_location = (
                location.strip()
            )

        if version.strip():
            self.current_version = (
                version.strip()
            )

        self.review_status = (
            DocumentationRequestStatus.SUBMITTED
        )

    def mark_under_review(
        self,
        reviewer: str = "",
    ) -> None:
        if not self.submitted:
            raise DRLModelError(
                "A request cannot enter review "
                "before it has been submitted."
            )

        if reviewer.strip():
            self.reviewer = reviewer.strip()

        self.review_status = (
            DocumentationRequestStatus.UNDER_REVIEW
        )

    def mark_accepted(
        self,
        *,
        reviewed_date: Optional[date] = None,
        reviewer: str = "",
        comments: str = "",
    ) -> None:
        if not self.submitted:
            raise DRLModelError(
                "A request cannot be accepted "
                "before it has been submitted."
            )

        actual_date = (
            reviewed_date
            or date.today()
        )

        if (
            self.date_submitted is not None
            and actual_date < self.date_submitted
        ):
            raise DRLModelError(
                "date_reviewed cannot be before "
                "date_submitted."
            )

        self.date_reviewed = actual_date

        if reviewer.strip():
            self.reviewer = reviewer.strip()

        if comments.strip():
            self.comments = comments.strip()

        self.review_status = (
            DocumentationRequestStatus.ACCEPTED
        )

    def mark_needs_revision(
        self,
        *,
        reviewed_date: Optional[date] = None,
        reviewer: str = "",
        comments: str = "",
    ) -> None:
        if not self.submitted:
            raise DRLModelError(
                "A submitted item is required "
                "before requesting revision."
            )

        actual_date = (
            reviewed_date
            or date.today()
        )

        if (
            self.date_submitted is not None
            and actual_date < self.date_submitted
        ):
            raise DRLModelError(
                "date_reviewed cannot be before "
                "date_submitted."
            )

        self.date_reviewed = actual_date

        if reviewer.strip():
            self.reviewer = reviewer.strip()

        if comments.strip():
            self.comments = comments.strip()

        self.review_status = (
            DocumentationRequestStatus.NEEDS_REVISION
        )

    def mark_not_applicable(
        self,
        comments: str = "",
    ) -> None:
        if comments.strip():
            self.comments = comments.strip()

        self.review_status = (
            DocumentationRequestStatus.NOT_APPLICABLE
        )

    @staticmethod
    def _deduplicate_controls(
        controls: Iterable[
            DocumentationRequestControl
        ],
    ) -> List[DocumentationRequestControl]:
        result: List[
            DocumentationRequestControl
        ] = []

        seen = set()

        for control in controls:
            if control.key in seen:
                continue

            seen.add(
                control.key
            )

            result.append(
                control
            )

        return result


@dataclass(frozen=True, slots=True)
class DocumentationRequestSummary:
    """Calculated DRL summary information."""

    total_requests: int

    high_priority: int
    medium_priority: int
    low_priority: int

    submitted: int
    pending: int
    under_review: int
    accepted: int
    needs_revision: int
    not_applicable: int

    overdue: int

    unique_controls_supported: int

    reused_requests: int

    total_control_mappings: int


@dataclass(slots=True)
class DocumentationRequestCollection:
    """
    Complete client-facing Documentation Request List.

    This becomes the input to both the Excel and Word DRL exporters.
    """

    framework_id: str

    engagement_name: str = ""

    organization_name: str = ""

    assessor_organization: str = ""

    engagement_start_date: Optional[date] = None

    requests: List[
        DocumentationRequest
    ] = field(
        default_factory=list
    )

    notes: str = ""

    def __post_init__(self) -> None:
        self.framework_id = self.framework_id.strip()
        self.engagement_name = self.engagement_name.strip()
        self.organization_name = self.organization_name.strip()
        self.assessor_organization = (
            self.assessor_organization.strip()
        )
        self.notes = self.notes.strip()

        if not self.framework_id:
            raise DRLModelError(
                "DocumentationRequestCollection.framework_id "
                "cannot be blank."
            )

        self.requests = self._deduplicate_requests(
            self.requests
        )

    @property
    def count(self) -> int:
        return len(self.requests)

    @property
    def summary(
        self,
    ) -> DocumentationRequestSummary:
        all_controls = set()

        total_control_mappings = 0
        reused_requests = 0

        for request in self.requests:
            total_control_mappings += (
                request.reuse_count
            )

            if request.is_reused:
                reused_requests += 1

            for control in request.controls:
                all_controls.add(
                    control.key
                )

        submitted = sum(
            request.submitted
            for request in self.requests
        )

        accepted = sum(
            request.review_status
            == DocumentationRequestStatus.ACCEPTED
            for request in self.requests
        )

        under_review = sum(
            request.review_status
            == DocumentationRequestStatus.UNDER_REVIEW
            for request in self.requests
        )

        needs_revision = sum(
            request.review_status
            == DocumentationRequestStatus.NEEDS_REVISION
            for request in self.requests
        )

        not_applicable = sum(
            request.review_status
            == DocumentationRequestStatus.NOT_APPLICABLE
            for request in self.requests
        )

        pending = sum(
            request.review_status
            in {
                DocumentationRequestStatus.NOT_REQUESTED,
                DocumentationRequestStatus.REQUESTED,
                DocumentationRequestStatus.PENDING,
            }
            for request in self.requests
        )

        overdue = sum(
            request.is_overdue
            for request in self.requests
        )

        high_priority = sum(
            request.priority
            == DocumentationRequestPriority.HIGH
            for request in self.requests
        )

        medium_priority = sum(
            request.priority
            == DocumentationRequestPriority.MEDIUM
            for request in self.requests
        )

        low_priority = sum(
            request.priority
            == DocumentationRequestPriority.LOW
            for request in self.requests
        )

        return DocumentationRequestSummary(
            total_requests=len(
                self.requests
            ),
            high_priority=high_priority,
            medium_priority=medium_priority,
            low_priority=low_priority,
            submitted=submitted,
            pending=pending,
            under_review=under_review,
            accepted=accepted,
            needs_revision=needs_revision,
            not_applicable=not_applicable,
            overdue=overdue,
            unique_controls_supported=len(
                all_controls
            ),
            reused_requests=reused_requests,
            total_control_mappings=(
                total_control_mappings
            ),
        )

    def add(
        self,
        request: DocumentationRequest,
    ) -> None:
        existing_ids = {
            item.request_id.casefold()
            for item in self.requests
        }

        if (
            request.request_id.casefold()
            in existing_ids
        ):
            raise DRLModelError(
                "Duplicate Documentation Request ID: "
                f"{request.request_id}"
            )

        self.requests.append(
            request
        )

    def get(
        self,
        request_id: str,
    ) -> DocumentationRequest:
        key = request_id.strip().casefold()

        for request in self.requests:
            if (
                request.request_id.casefold()
                == key
            ):
                return request

        raise DRLModelError(
            "Documentation Request not found: "
            f"{request_id}"
        )

    @staticmethod
    def _deduplicate_requests(
        requests: Sequence[
            DocumentationRequest
        ],
    ) -> List[DocumentationRequest]:
        result: List[
            DocumentationRequest
        ] = []

        seen = set()

        for request in requests:
            key = (
                request.request_id.casefold()
            )

            if key in seen:
                raise DRLModelError(
                    "Duplicate Documentation Request ID: "
                    f"{request.request_id}"
                )

            seen.add(key)
            result.append(request)

        return result