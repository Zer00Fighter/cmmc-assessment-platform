from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from src.assessment_knowledge.models import (
    CompiledAssessmentKnowledge,
    CompiledEvidence,
    CompiledRequirement,
)
from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestControl,
    DocumentationRequestPriority,
    DocumentationRequestStatus,
    DocumentationRequestType,
)


class RequestGeneratorError(ValueError):
    """Raised when a Documentation Request List cannot be generated."""


@dataclass(frozen=True, slots=True)
class RequestGeneratorOptions:
    request_prefix: str = "DRL"
    high_priority_reuse_threshold: int = 5
    medium_priority_reuse_threshold: int = 2
    default_status: DocumentationRequestStatus = (
        DocumentationRequestStatus.NOT_REQUESTED
    )

    def __post_init__(self) -> None:
        prefix = self.request_prefix.strip()

        if not prefix:
            raise RequestGeneratorError(
                "RequestGeneratorOptions.request_prefix cannot be blank."
            )

        if self.high_priority_reuse_threshold < 1:
            raise RequestGeneratorError(
                "high_priority_reuse_threshold must be at least 1."
            )

        if self.medium_priority_reuse_threshold < 1:
            raise RequestGeneratorError(
                "medium_priority_reuse_threshold must be at least 1."
            )

        if (
            self.high_priority_reuse_threshold
            < self.medium_priority_reuse_threshold
        ):
            raise RequestGeneratorError(
                "high_priority_reuse_threshold cannot be lower than "
                "medium_priority_reuse_threshold."
            )

        object.__setattr__(
            self,
            "request_prefix",
            prefix,
        )


class RequestGenerator:
    """
    Generate a client-facing Documentation Request List from compiled
    assessment knowledge.

    Initial scope: generate documentation requests from compiled evidence
    objects only. Interview and Test objects remain in the knowledge graph
    for assessor-facing work products.
    """

    def __init__(
        self,
        options: RequestGeneratorOptions | None = None,
    ) -> None:
        self.options = (
            options
            or RequestGeneratorOptions()
        )

    def generate(
        self,
        knowledge: CompiledAssessmentKnowledge,
        *,
        framework_id: str,
        engagement_name: str = "",
        organization_name: str = "",
        assessor_organization: str = "",
        notes: str = "",
    ) -> DocumentationRequestCollection:
        framework_id = framework_id.strip()

        if not framework_id:
            raise RequestGeneratorError(
                "framework_id cannot be blank."
            )

        requirements = self._requirements_for_framework(
            knowledge,
            framework_id,
        )

        requirement_index = {
            requirement.requirement_id.casefold(): requirement
            for requirement in requirements
        }

        evidence = self._evidence_for_framework(
            knowledge.evidence,
            framework_id,
        )

        requests: List[DocumentationRequest] = []

        for sequence, item in enumerate(
            evidence,
            start=1,
        ):
            controls = self._controls_for_evidence(
                item,
                framework_id=framework_id,
                requirement_index=requirement_index,
            )

            if not controls:
                continue

            requests.append(
                DocumentationRequest(
                    request_id=self._request_id(sequence),
                    requested_item=item.title,
                    evidence_type=self._evidence_type(item),
                    priority=self._priority(len(controls)),
                    controls=controls,
                    description=self._description(item),
                    review_status=self.options.default_status,
                    generated=True,
                )
            )

        return DocumentationRequestCollection(
            framework_id=framework_id,
            engagement_name=engagement_name,
            organization_name=organization_name,
            assessor_organization=assessor_organization,
            requests=requests,
            notes=notes,
        )

    def _request_id(
        self,
        sequence: int,
    ) -> str:
        return (
            f"{self.options.request_prefix}-"
            f"{sequence:03d}"
        )

    @staticmethod
    def _requirements_for_framework(
        knowledge: CompiledAssessmentKnowledge,
        framework_id: str,
    ) -> Tuple[CompiledRequirement, ...]:
        key = framework_id.casefold()

        return tuple(
            sorted(
                (
                    requirement
                    for requirement in knowledge.requirements
                    if requirement.framework_id.casefold() == key
                ),
                key=lambda item: item.requirement_id.casefold(),
            )
        )

    @staticmethod
    def _evidence_for_framework(
        evidence: Sequence[CompiledEvidence],
        framework_id: str,
    ) -> Tuple[CompiledEvidence, ...]:
        key = framework_id.casefold()

        return tuple(
            sorted(
                (
                    item
                    for item in evidence
                    if any(
                        value.casefold() == key
                        for value in item.framework_ids
                    )
                ),
                key=lambda item: item.canonical_id.casefold(),
            )
        )

    def _controls_for_evidence(
        self,
        evidence: CompiledEvidence,
        *,
        framework_id: str,
        requirement_index: Dict[
            str,
            CompiledRequirement,
        ],
    ) -> List[DocumentationRequestControl]:
        framework_key = framework_id.casefold()

        requirement_ids: List[str] = []
        seen = set()

        for source in evidence.sources:
            if (
                source.framework_id.casefold()
                != framework_key
            ):
                continue

            requirement_id = source.requirement_id.strip()

            if not requirement_id:
                continue

            key = requirement_id.casefold()

            if key in seen:
                continue

            seen.add(key)
            requirement_ids.append(requirement_id)

        if not requirement_ids:
            for requirement_id in evidence.requirement_ids:
                key = requirement_id.strip().casefold()

                if (
                    not key
                    or key in seen
                    or key not in requirement_index
                ):
                    continue

                seen.add(key)
                requirement_ids.append(
                    requirement_id.strip()
                )

        controls: List[DocumentationRequestControl] = []

        for requirement_id in sorted(
            requirement_ids,
            key=str.casefold,
        ):
            requirement = requirement_index.get(
                requirement_id.casefold()
            )

            if requirement is None:
                raise RequestGeneratorError(
                    "Evidence object "
                    f"{evidence.canonical_id!r} references "
                    "a requirement that is not present "
                    f"in framework {framework_id!r}: "
                    f"{requirement_id!r}."
                )

            controls.append(
                DocumentationRequestControl(
                    framework_id=requirement.framework_id,
                    control_id=requirement.requirement_id,
                    family=requirement.family,
                    control_title=requirement.title,
                )
            )

        return controls

    def _priority(
        self,
        reuse_count: int,
    ) -> DocumentationRequestPriority:
        if (
            reuse_count
            >= self.options.high_priority_reuse_threshold
        ):
            return DocumentationRequestPriority.HIGH

        if (
            reuse_count
            >= self.options.medium_priority_reuse_threshold
        ):
            return DocumentationRequestPriority.MEDIUM

        return DocumentationRequestPriority.LOW

    @staticmethod
    def _description(
        evidence: CompiledEvidence,
    ) -> str:
        values: List[str] = []
        seen = set()

        for value in evidence.raw_descriptions:
            text = value.strip()

            if not text:
                continue

            key = text.casefold()

            if key in seen:
                continue

            seen.add(key)
            values.append(text)

        if values:
            return " | ".join(values)

        return (
            "Provide the requested documentation or "
            f"evidence for {evidence.title}."
        )

    @classmethod
    def _evidence_type(
        cls,
        evidence: CompiledEvidence,
    ) -> DocumentationRequestType:
        haystack = " ".join(
            (
                evidence.title,
                evidence.object_type,
                *evidence.raw_descriptions,
            )
        ).casefold()

        rules = (
            (
                ("system security plan", "ssp"),
                DocumentationRequestType.SYSTEM_SECURITY_PLAN,
            ),
            (
                ("configuration baseline", "baseline configuration"),
                DocumentationRequestType.CONFIGURATION_BASELINE,
            ),
            (
                ("risk assessment",),
                DocumentationRequestType.RISK_ASSESSMENT,
            ),
            (
                ("security assessment",),
                DocumentationRequestType.SECURITY_ASSESSMENT,
            ),
            (
                ("plan of action", "poa&m", "poam"),
                DocumentationRequestType.POAM,
            ),
            (
                ("training record",),
                DocumentationRequestType.TRAINING_RECORD,
            ),
            (
                ("personnel record", "personnel records"),
                DocumentationRequestType.PERSONNEL_RECORD,
            ),
            (
                ("interconnection agreement", "interconnection"),
                DocumentationRequestType.INTERCONNECTION,
            ),
            (
                ("agreement",),
                DocumentationRequestType.AGREEMENT,
            ),
            (
                ("contract", "contractual"),
                DocumentationRequestType.CONTRACT,
            ),
            (
                ("diagram",),
                DocumentationRequestType.DIAGRAM,
            ),
            (
                ("inventory",),
                DocumentationRequestType.INVENTORY,
            ),
            (
                ("audit log", "system log", "logs", " log "),
                DocumentationRequestType.LOG,
            ),
            (
                ("report",),
                DocumentationRequestType.REPORT,
            ),
            (
                ("record", "records"),
                DocumentationRequestType.RECORD,
            ),
            (
                ("screenshot",),
                DocumentationRequestType.SCREENSHOT,
            ),
            (
                ("configuration setting", "configuration settings", "configuration"),
                DocumentationRequestType.CONFIGURATION,
            ),
            (
                ("procedure",),
                DocumentationRequestType.PROCEDURE,
            ),
            (
                ("policy",),
                DocumentationRequestType.POLICY,
            ),
            (
                ("standard",),
                DocumentationRequestType.STANDARD,
            ),
            (
                ("plan",),
                DocumentationRequestType.PLAN,
            ),
        )

        padded = f" {haystack} "

        for terms, request_type in rules:
            if any(term in padded for term in terms):
                return request_type

        return DocumentationRequestType.OTHER