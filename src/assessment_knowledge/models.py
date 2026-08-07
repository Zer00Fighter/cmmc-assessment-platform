from __future__ import annotations

import hashlib

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Optional, Sequence, Tuple


class AssessmentKnowledgeModelError(ValueError):
    """Raised when compiled assessment knowledge is invalid."""


class AssessmentMethodKind(str, Enum):
    """Framework-neutral assessment method."""

    EXAMINE = "Examine"
    INTERVIEW = "Interview"
    TEST = "Test"
    OBSERVE = "Observe"
    OTHER = "Other"


class KnowledgeObjectType(str, Enum):
    """Generic compiled knowledge object types."""

    REQUIREMENT = "Requirement"
    OBJECTIVE = "Objective"
    EVIDENCE = "Evidence"
    INTERVIEW = "Interview"
    TEST = "Test"


@dataclass(frozen=True, slots=True)
class SourceReference:
    """
    Provenance for compiled assessment knowledge.

    A SourceReference answers:

        Where did this knowledge come from?
        Which framework introduced it?
        Which requirement/objective referenced it?
        Which assessment method produced it?
    """

    framework_id: str

    family: str = ""

    requirement_id: str = ""

    objective_id: str = ""

    method: Optional[AssessmentMethodKind] = None

    source_document: str = ""

    source_revision: str = ""

    source_location: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()

        if not framework_id:
            raise AssessmentKnowledgeModelError(
                "SourceReference.framework_id cannot be blank."
            )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        for name in (
            "family",
            "requirement_id",
            "objective_id",
            "source_document",
            "source_revision",
            "source_location",
        ):
            value = getattr(
                self,
                name,
            )

            object.__setattr__(
                self,
                name,
                value.strip(),
            )

    @property
    def key(self) -> Tuple[str, ...]:
        return (
            self.framework_id.casefold(),
            self.family.casefold(),
            self.requirement_id.casefold(),
            self.objective_id.casefold(),
            (
                self.method.value.casefold()
                if self.method
                else ""
            ),
            self.source_document.casefold(),
            self.source_revision.casefold(),
            self.source_location.casefold(),
        )


@dataclass(frozen=True, slots=True)
class CompiledObjective:
    """Compiled assessment objective."""

    framework_id: str
    requirement_id: str
    objective_id: str
    objective_text: str

    evidence_ids: Sequence[str] = field(
        default_factory=tuple
    )

    interview_ids: Sequence[str] = field(
        default_factory=tuple
    )

    test_ids: Sequence[str] = field(
        default_factory=tuple
    )

    sources: Sequence[SourceReference] = field(
        default_factory=tuple
    )

    guid: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        requirement_id = self.requirement_id.strip()
        objective_id = self.objective_id.strip()
        objective_text = self.objective_text.strip()

        if not framework_id:
            raise AssessmentKnowledgeModelError(
                "CompiledObjective.framework_id cannot be blank."
            )

        if not requirement_id:
            raise AssessmentKnowledgeModelError(
                "CompiledObjective.requirement_id cannot be blank."
            )

        if not objective_id:
            raise AssessmentKnowledgeModelError(
                "CompiledObjective.objective_id cannot be blank."
            )

        if not objective_text:
            raise AssessmentKnowledgeModelError(
                "CompiledObjective.objective_text cannot be blank."
            )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        object.__setattr__(
            self,
            "requirement_id",
            requirement_id,
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

        object.__setattr__(
            self,
            "evidence_ids",
            _normalized_ids(
                self.evidence_ids
            ),
        )

        object.__setattr__(
            self,
            "interview_ids",
            _normalized_ids(
                self.interview_ids
            ),
        )

        object.__setattr__(
            self,
            "test_ids",
            _normalized_ids(
                self.test_ids
            ),
        )

        object.__setattr__(
            self,
            "sources",
            _deduplicate_sources(
                self.sources
            ),
        )

        if not self.guid:
            object.__setattr__(
                self,
                "guid",
                stable_guid(
                    "objective",
                    framework_id,
                    requirement_id,
                    objective_id,
                ),
            )


@dataclass(frozen=True, slots=True)
class CompiledRequirement:
    """Compiled framework requirement/control."""

    framework_id: str
    requirement_id: str
    family: str
    title: str
    requirement_text: str

    sprs_weight: Optional[int] = None

    objective_ids: Sequence[str] = field(
        default_factory=tuple
    )

    evidence_ids: Sequence[str] = field(
        default_factory=tuple
    )

    interview_ids: Sequence[str] = field(
        default_factory=tuple
    )

    test_ids: Sequence[str] = field(
        default_factory=tuple
    )

    sources: Sequence[SourceReference] = field(
        default_factory=tuple
    )

    guid: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        requirement_id = self.requirement_id.strip()
        family = self.family.strip()
        title = self.title.strip()
        requirement_text = self.requirement_text.strip()

        if not framework_id:
            raise AssessmentKnowledgeModelError(
                "CompiledRequirement.framework_id cannot be blank."
            )

        if not requirement_id:
            raise AssessmentKnowledgeModelError(
                "CompiledRequirement.requirement_id cannot be blank."
            )

        if not requirement_text:
            raise AssessmentKnowledgeModelError(
                "CompiledRequirement.requirement_text cannot be blank."
            )

        if (
            self.sprs_weight is not None
            and self.sprs_weight < 0
        ):
            raise AssessmentKnowledgeModelError(
                "CompiledRequirement.sprs_weight cannot be negative."
            )

        object.__setattr__(
            self,
            "framework_id",
            framework_id,
        )

        object.__setattr__(
            self,
            "requirement_id",
            requirement_id,
        )

        object.__setattr__(
            self,
            "family",
            family,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "requirement_text",
            requirement_text,
        )

        object.__setattr__(
            self,
            "objective_ids",
            _normalized_ids(
                self.objective_ids
            ),
        )

        object.__setattr__(
            self,
            "evidence_ids",
            _normalized_ids(
                self.evidence_ids
            ),
        )

        object.__setattr__(
            self,
            "interview_ids",
            _normalized_ids(
                self.interview_ids
            ),
        )

        object.__setattr__(
            self,
            "test_ids",
            _normalized_ids(
                self.test_ids
            ),
        )

        object.__setattr__(
            self,
            "sources",
            _deduplicate_sources(
                self.sources
            ),
        )

        if not self.guid:
            object.__setattr__(
                self,
                "guid",
                stable_guid(
                    "requirement",
                    framework_id,
                    requirement_id,
                ),
            )


@dataclass(frozen=True, slots=True)
class CompiledEvidence:
    """
    Unique evidence object compiled from assessment methods.

    One evidence object may support many requirements and objectives.
    """

    canonical_id: str
    title: str
    object_type: str

    framework_ids: Sequence[str] = field(
        default_factory=tuple
    )

    requirement_ids: Sequence[str] = field(
        default_factory=tuple
    )

    objective_ids: Sequence[str] = field(
        default_factory=tuple
    )

    source_methods: Sequence[
        AssessmentMethodKind
    ] = field(
        default_factory=tuple
    )

    raw_descriptions: Sequence[str] = field(
        default_factory=tuple
    )

    sources: Sequence[SourceReference] = field(
        default_factory=tuple
    )

    guid: str = ""

    def __post_init__(self) -> None:
        canonical_id = self.canonical_id.strip()
        title = self.title.strip()
        object_type = self.object_type.strip()

        if not canonical_id:
            raise AssessmentKnowledgeModelError(
                "CompiledEvidence.canonical_id cannot be blank."
            )

        if not title:
            raise AssessmentKnowledgeModelError(
                "CompiledEvidence.title cannot be blank."
            )

        if not object_type:
            raise AssessmentKnowledgeModelError(
                "CompiledEvidence.object_type cannot be blank."
            )

        object.__setattr__(
            self,
            "canonical_id",
            canonical_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "object_type",
            object_type,
        )

        object.__setattr__(
            self,
            "framework_ids",
            _normalized_ids(
                self.framework_ids
            ),
        )

        object.__setattr__(
            self,
            "requirement_ids",
            _normalized_ids(
                self.requirement_ids
            ),
        )

        object.__setattr__(
            self,
            "objective_ids",
            _normalized_ids(
                self.objective_ids
            ),
        )

        object.__setattr__(
            self,
            "source_methods",
            _deduplicate_methods(
                self.source_methods
            ),
        )

        object.__setattr__(
            self,
            "raw_descriptions",
            _normalized_text_values(
                self.raw_descriptions
            ),
        )

        object.__setattr__(
            self,
            "sources",
            _deduplicate_sources(
                self.sources
            ),
        )

        if not self.guid:
            object.__setattr__(
                self,
                "guid",
                stable_guid(
                    "evidence",
                    canonical_id,
                ),
            )

    @property
    def reused(self) -> bool:
        return len(
            self.requirement_ids
        ) > 1

    @property
    def requirement_count(self) -> int:
        return len(
            self.requirement_ids
        )

    @property
    def framework_count(self) -> int:
        return len(
            self.framework_ids
        )


@dataclass(frozen=True, slots=True)
class CompiledInterview:
    """Unique compiled interview subject."""

    canonical_id: str
    title: str

    framework_ids: Sequence[str] = field(
        default_factory=tuple
    )

    requirement_ids: Sequence[str] = field(
        default_factory=tuple
    )

    objective_ids: Sequence[str] = field(
        default_factory=tuple
    )

    raw_descriptions: Sequence[str] = field(
        default_factory=tuple
    )

    sources: Sequence[SourceReference] = field(
        default_factory=tuple
    )

    guid: str = ""

    def __post_init__(self) -> None:
        canonical_id = self.canonical_id.strip()
        title = self.title.strip()

        if not canonical_id:
            raise AssessmentKnowledgeModelError(
                "CompiledInterview.canonical_id cannot be blank."
            )

        if not title:
            raise AssessmentKnowledgeModelError(
                "CompiledInterview.title cannot be blank."
            )

        object.__setattr__(
            self,
            "canonical_id",
            canonical_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "framework_ids",
            _normalized_ids(
                self.framework_ids
            ),
        )

        object.__setattr__(
            self,
            "requirement_ids",
            _normalized_ids(
                self.requirement_ids
            ),
        )

        object.__setattr__(
            self,
            "objective_ids",
            _normalized_ids(
                self.objective_ids
            ),
        )

        object.__setattr__(
            self,
            "raw_descriptions",
            _normalized_text_values(
                self.raw_descriptions
            ),
        )

        object.__setattr__(
            self,
            "sources",
            _deduplicate_sources(
                self.sources
            ),
        )

        if not self.guid:
            object.__setattr__(
                self,
                "guid",
                stable_guid(
                    "interview",
                    canonical_id,
                ),
            )

    @property
    def reused(self) -> bool:
        return len(
            self.requirement_ids
        ) > 1


@dataclass(frozen=True, slots=True)
class CompiledTest:
    """Unique compiled technical test or demonstration target."""

    canonical_id: str
    title: str

    framework_ids: Sequence[str] = field(
        default_factory=tuple
    )

    requirement_ids: Sequence[str] = field(
        default_factory=tuple
    )

    objective_ids: Sequence[str] = field(
        default_factory=tuple
    )

    raw_descriptions: Sequence[str] = field(
        default_factory=tuple
    )

    sources: Sequence[SourceReference] = field(
        default_factory=tuple
    )

    guid: str = ""

    def __post_init__(self) -> None:
        canonical_id = self.canonical_id.strip()
        title = self.title.strip()

        if not canonical_id:
            raise AssessmentKnowledgeModelError(
                "CompiledTest.canonical_id cannot be blank."
            )

        if not title:
            raise AssessmentKnowledgeModelError(
                "CompiledTest.title cannot be blank."
            )

        object.__setattr__(
            self,
            "canonical_id",
            canonical_id,
        )

        object.__setattr__(
            self,
            "title",
            title,
        )

        object.__setattr__(
            self,
            "framework_ids",
            _normalized_ids(
                self.framework_ids
            ),
        )

        object.__setattr__(
            self,
            "requirement_ids",
            _normalized_ids(
                self.requirement_ids
            ),
        )

        object.__setattr__(
            self,
            "objective_ids",
            _normalized_ids(
                self.objective_ids
            ),
        )

        object.__setattr__(
            self,
            "raw_descriptions",
            _normalized_text_values(
                self.raw_descriptions
            ),
        )

        object.__setattr__(
            self,
            "sources",
            _deduplicate_sources(
                self.sources
            ),
        )

        if not self.guid:
            object.__setattr__(
                self,
                "guid",
                stable_guid(
                    "test",
                    canonical_id,
                ),
            )

    @property
    def reused(self) -> bool:
        return len(
            self.requirement_ids
        ) > 1


@dataclass(frozen=True, slots=True)
class KnowledgeStatistics:
    """Summary statistics for compiled assessment knowledge."""

    requirement_count: int
    objective_count: int
    evidence_count: int
    reusable_evidence_count: int
    interview_count: int
    test_count: int

    average_evidence_per_requirement: float
    average_objectives_per_requirement: float


@dataclass(frozen=True, slots=True)
class CompiledAssessmentKnowledge:
    """
    Root in-memory model for one or more compiled frameworks.

    Everything downstream should consume this object rather than
    parsing authoritative assessment source files independently.
    """

    requirements: Sequence[
        CompiledRequirement
    ] = field(
        default_factory=tuple
    )

    objectives: Sequence[
        CompiledObjective
    ] = field(
        default_factory=tuple
    )

    evidence: Sequence[
        CompiledEvidence
    ] = field(
        default_factory=tuple
    )

    interviews: Sequence[
        CompiledInterview
    ] = field(
        default_factory=tuple
    )

    tests: Sequence[
        CompiledTest
    ] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requirements",
            tuple(
                self.requirements
            ),
        )

        object.__setattr__(
            self,
            "objectives",
            tuple(
                self.objectives
            ),
        )

        object.__setattr__(
            self,
            "evidence",
            tuple(
                self.evidence
            ),
        )

        object.__setattr__(
            self,
            "interviews",
            tuple(
                self.interviews
            ),
        )

        object.__setattr__(
            self,
            "tests",
            tuple(
                self.tests
            ),
        )

        self._validate_unique_ids()

    def _validate_unique_ids(
        self,
    ) -> None:
        _require_unique(
            (
                item.guid
                for item in self.requirements
            ),
            "requirement GUID",
        )

        _require_unique(
            (
                item.guid
                for item in self.objectives
            ),
            "objective GUID",
        )

        _require_unique(
            (
                item.canonical_id
                for item in self.evidence
            ),
            "evidence canonical ID",
        )

        _require_unique(
            (
                item.canonical_id
                for item in self.interviews
            ),
            "interview canonical ID",
        )

        _require_unique(
            (
                item.canonical_id
                for item in self.tests
            ),
            "test canonical ID",
        )

    @property
    def requirement_index(
        self,
    ) -> Dict[str, CompiledRequirement]:
        return {
            _framework_control_key(
                item.framework_id,
                item.requirement_id,
            ): item
            for item in self.requirements
        }

    @property
    def objective_index(
        self,
    ) -> Dict[str, CompiledObjective]:
        return {
            _objective_key(
                item.framework_id,
                item.requirement_id,
                item.objective_id,
            ): item
            for item in self.objectives
        }

    @property
    def evidence_index(
        self,
    ) -> Dict[str, CompiledEvidence]:
        return {
            item.canonical_id: item
            for item in self.evidence
        }

    @property
    def interview_index(
        self,
    ) -> Dict[str, CompiledInterview]:
        return {
            item.canonical_id: item
            for item in self.interviews
        }

    @property
    def test_index(
        self,
    ) -> Dict[str, CompiledTest]:
        return {
            item.canonical_id: item
            for item in self.tests
        }

    @property
    def framework_ids(
        self,
    ) -> Tuple[str, ...]:
        values = {
            item.framework_id
            for item in self.requirements
        }

        return tuple(
            sorted(
                values,
                key=str.casefold,
            )
        )

    @property
    def statistics(
        self,
    ) -> KnowledgeStatistics:
        requirement_count = len(
            self.requirements
        )

        objective_count = len(
            self.objectives
        )

        evidence_count = len(
            self.evidence
        )

        reusable_evidence_count = sum(
            item.reused
            for item in self.evidence
        )

        interview_count = len(
            self.interviews
        )

        test_count = len(
            self.tests
        )

        total_evidence_links = sum(
            len(
                item.evidence_ids
            )
            for item in self.requirements
        )

        average_evidence = (
            0.0
            if requirement_count == 0
            else (
                total_evidence_links
                / requirement_count
            )
        )

        total_objective_links = sum(
            len(
                item.objective_ids
            )
            for item in self.requirements
        )

        average_objectives = (
            0.0
            if requirement_count == 0
            else (
                total_objective_links
                / requirement_count
            )
        )

        return KnowledgeStatistics(
            requirement_count=requirement_count,
            objective_count=objective_count,
            evidence_count=evidence_count,
            reusable_evidence_count=(
                reusable_evidence_count
            ),
            interview_count=interview_count,
            test_count=test_count,
            average_evidence_per_requirement=round(
                average_evidence,
                2,
            ),
            average_objectives_per_requirement=round(
                average_objectives,
                2,
            ),
        )

    def get_requirement(
        self,
        framework_id: str,
        requirement_id: str,
    ) -> CompiledRequirement:
        key = _framework_control_key(
            framework_id,
            requirement_id,
        )

        try:
            return self.requirement_index[
                key
            ]

        except KeyError as error:
            raise AssessmentKnowledgeModelError(
                "Compiled requirement not found: "
                f"{framework_id}/{requirement_id}"
            ) from error

    def get_objective(
        self,
        framework_id: str,
        requirement_id: str,
        objective_id: str,
    ) -> CompiledObjective:
        key = _objective_key(
            framework_id,
            requirement_id,
            objective_id,
        )

        try:
            return self.objective_index[
                key
            ]

        except KeyError as error:
            raise AssessmentKnowledgeModelError(
                "Compiled objective not found: "
                f"{framework_id}/"
                f"{requirement_id}/"
                f"{objective_id}"
            ) from error

    def get_evidence(
        self,
        canonical_id: str,
    ) -> CompiledEvidence:
        try:
            return self.evidence_index[
                canonical_id
            ]

        except KeyError as error:
            raise AssessmentKnowledgeModelError(
                "Compiled evidence not found: "
                f"{canonical_id}"
            ) from error


def stable_guid(
    *parts: object,
) -> str:
    """
    Produce a deterministic internal GUID.

    We deliberately use a deterministic hash rather than uuid4 so
    recompiling identical framework knowledge produces identical IDs.
    """

    normalized = "::".join(
        str(part)
        .strip()
        .casefold()
        for part in parts
    )

    if not normalized:
        raise AssessmentKnowledgeModelError(
            "Cannot generate a stable GUID "
            "from empty values."
        )

    digest = hashlib.sha256(
        normalized.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"{digest[0:8]}-"
        f"{digest[8:12]}-"
        f"{digest[12:16]}-"
        f"{digest[16:20]}-"
        f"{digest[20:32]}"
    )


def _normalized_ids(
    values: Iterable[str],
) -> Tuple[str, ...]:
    result = []
    seen = set()

    for value in values:
        normalized = str(
            value
        ).strip()

        if not normalized:
            continue

        key = normalized.casefold()

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            normalized
        )

    return tuple(
        result
    )


def _normalized_text_values(
    values: Iterable[str],
) -> Tuple[str, ...]:
    return _normalized_ids(
        values
    )


def _deduplicate_methods(
    methods: Iterable[
        AssessmentMethodKind
    ],
) -> Tuple[AssessmentMethodKind, ...]:
    result = []
    seen = set()

    for method in methods:
        if method in seen:
            continue

        seen.add(
            method
        )

        result.append(
            method
        )

    return tuple(
        result
    )


def _deduplicate_sources(
    sources: Iterable[
        SourceReference
    ],
) -> Tuple[SourceReference, ...]:
    result = []
    seen = set()

    for source in sources:
        if source.key in seen:
            continue

        seen.add(
            source.key
        )

        result.append(
            source
        )

    return tuple(
        result
    )


def _require_unique(
    values: Iterable[str],
    description: str,
) -> None:
    seen = set()

    for value in values:
        key = value.casefold()

        if key in seen:
            raise AssessmentKnowledgeModelError(
                f"Duplicate {description}: {value}"
            )

        seen.add(
            key
        )


def _framework_control_key(
    framework_id: str,
    requirement_id: str,
) -> str:
    return (
        f"{framework_id.strip().casefold()}"
        "::"
        f"{requirement_id.strip().casefold()}"
    )


def _objective_key(
    framework_id: str,
    requirement_id: str,
    objective_id: str,
) -> str:
    return (
        f"{framework_id.strip().casefold()}"
        "::"
        f"{requirement_id.strip().casefold()}"
        "::"
        f"{objective_id.strip().casefold()}"
    )