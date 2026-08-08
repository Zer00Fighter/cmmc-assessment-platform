from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.assessment_knowledge.models import (
    AssessmentMethodKind,
    CompiledAssessmentKnowledge,
    CompiledEvidence,
    CompiledInterview,
    CompiledObjective,
    CompiledRequirement,
    CompiledTest,
    SourceReference,
)
from src.evidence_requests.assessment_method_parser import (
    AssessmentMethodParser,
    AssessmentMethodType,
    AssessmentObject,
)


class CatalogCompilerError(ValueError):
    """Raised when assessment knowledge cannot be compiled."""


@dataclass(frozen=True, slots=True)
class AssessmentProcedureRow:
    """
    Framework-neutral normalized assessment procedure row.

    A row may represent either:
      - a requirement-level record, or
      - an objective-level record.
    """

    framework_id: str
    family: str
    requirement_id: str
    requirement_title: str
    requirement_text: str

    objective_id: str = ""
    objective_text: str = ""

    examine: str = ""
    interview: str = ""
    test: str = ""

    sprs_weight: Optional[int] = None

    source_document: str = ""
    source_revision: str = ""
    source_location: str = ""

    def __post_init__(self) -> None:
        framework_id = self.framework_id.strip()
        family = self.family.strip()
        requirement_id = self.requirement_id.strip()
        requirement_title = self.requirement_title.strip()
        requirement_text = self.requirement_text.strip()
        objective_id = self.objective_id.strip()
        objective_text = self.objective_text.strip()

        if not framework_id:
            raise CatalogCompilerError(
                "AssessmentProcedureRow.framework_id cannot be blank."
            )

        if not requirement_id:
            raise CatalogCompilerError(
                "AssessmentProcedureRow.requirement_id cannot be blank."
            )

        if not requirement_text:
            raise CatalogCompilerError(
                "AssessmentProcedureRow.requirement_text cannot be blank."
            )

        if objective_id and not objective_text:
            raise CatalogCompilerError(
                "objective_text cannot be blank when objective_id is provided."
            )

        if self.sprs_weight is not None and self.sprs_weight < 0:
            raise CatalogCompilerError(
                "sprs_weight cannot be negative."
            )

        object.__setattr__(self, "framework_id", framework_id)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "requirement_title", requirement_title)
        object.__setattr__(self, "requirement_text", requirement_text)
        object.__setattr__(self, "objective_id", objective_id)
        object.__setattr__(self, "objective_text", objective_text)

        for field_name in (
            "examine",
            "interview",
            "test",
            "source_document",
            "source_revision",
            "source_location",
        ):
            object.__setattr__(
                self,
                field_name,
                getattr(self, field_name).strip(),
            )

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
    ) -> "AssessmentProcedureRow":
        if not isinstance(data, Mapping):
            raise CatalogCompilerError(
                "Assessment procedure row must be a mapping."
            )

        sprs_raw = data.get("sprs_weight")

        sprs_weight = (
            None
            if sprs_raw in (None, "")
            else int(sprs_raw)
        )

        return cls(
            framework_id=str(
                data.get("framework_id", "")
            ),
            family=str(
                data.get("family", "")
            ),
            requirement_id=str(
                data.get("requirement_id", "")
            ),
            requirement_title=str(
                data.get("requirement_title", "")
            ),
            requirement_text=str(
                data.get("requirement_text", "")
            ),
            objective_id=str(
                data.get("objective_id", "")
            ),
            objective_text=str(
                data.get("objective_text", "")
            ),
            examine=str(
                data.get("examine", "")
                or ""
            ),
            interview=str(
                data.get("interview", "")
                or ""
            ),
            test=str(
                data.get("test", "")
                or ""
            ),
            sprs_weight=sprs_weight,
            source_document=str(
                data.get("source_document", "")
            ),
            source_revision=str(
                data.get("source_revision", "")
            ),
            source_location=str(
                data.get("source_location", "")
            ),
        )


@dataclass
class _RequirementAccumulator:
    framework_id: str
    family: str
    requirement_id: str
    title: str
    requirement_text: str
    sprs_weight: Optional[int]

    objective_ids: List[str] = field(
        default_factory=list
    )
    evidence_ids: List[str] = field(
        default_factory=list
    )
    interview_ids: List[str] = field(
        default_factory=list
    )
    test_ids: List[str] = field(
        default_factory=list
    )
    sources: List[SourceReference] = field(
        default_factory=list
    )


@dataclass
class _ObjectiveAccumulator:
    framework_id: str
    requirement_id: str
    objective_id: str
    objective_text: str

    evidence_ids: List[str] = field(
        default_factory=list
    )
    interview_ids: List[str] = field(
        default_factory=list
    )
    test_ids: List[str] = field(
        default_factory=list
    )
    sources: List[SourceReference] = field(
        default_factory=list
    )


@dataclass
class _ObjectAccumulator:
    canonical_id: str
    title: str
    object_type: str

    framework_ids: List[str] = field(
        default_factory=list
    )
    requirement_ids: List[str] = field(
        default_factory=list
    )
    objective_ids: List[str] = field(
        default_factory=list
    )
    raw_descriptions: List[str] = field(
        default_factory=list
    )
    sources: List[SourceReference] = field(
        default_factory=list
    )


class CatalogCompiler:
    """
    Compile normalized assessment-procedure rows into one
    framework-neutral CompiledAssessmentKnowledge graph.
    """

    def __init__(
        self,
        parser: AssessmentMethodParser | None = None,
    ) -> None:
        self.parser = (
            parser
            or AssessmentMethodParser()
        )

    def compile(
        self,
        rows: Iterable[
            AssessmentProcedureRow | Mapping[str, Any]
        ],
    ) -> CompiledAssessmentKnowledge:
        normalized_rows = [
            self._coerce_row(row)
            for row in rows
        ]

        requirements: Dict[
            Tuple[str, str],
            _RequirementAccumulator,
        ] = {}

        objectives: Dict[
            Tuple[str, str, str],
            _ObjectiveAccumulator,
        ] = {}

        evidence: Dict[
            str,
            _ObjectAccumulator,
        ] = {}

        interviews: Dict[
            str,
            _ObjectAccumulator,
        ] = {}

        tests: Dict[
            str,
            _ObjectAccumulator,
        ] = {}

        for row in normalized_rows:
            requirement = (
                self._get_or_create_requirement(
                    requirements,
                    row,
                )
            )

            requirement_source = (
                self._source(
                    row,
                    method=None,
                )
            )

            self._append_unique(
                requirement.sources,
                requirement_source,
                key=lambda item: item.key,
            )

            objective = None

            if row.objective_id:
                objective = (
                    self._get_or_create_objective(
                        objectives,
                        row,
                    )
                )

                self._append_unique(
                    requirement.objective_ids,
                    row.objective_id,
                )

            self._compile_method(
                row=row,
                method_type=(
                    AssessmentMethodType.EXAMINE
                ),
                raw_text=row.examine,
                requirement=requirement,
                objective=objective,
                target=evidence,
            )

            self._compile_method(
                row=row,
                method_type=(
                    AssessmentMethodType.INTERVIEW
                ),
                raw_text=row.interview,
                requirement=requirement,
                objective=objective,
                target=interviews,
            )

            self._compile_method(
                row=row,
                method_type=(
                    AssessmentMethodType.TEST
                ),
                raw_text=row.test,
                requirement=requirement,
                objective=objective,
                target=tests,
            )

        compiled_requirements = tuple(
            CompiledRequirement(
                framework_id=item.framework_id,
                requirement_id=item.requirement_id,
                family=item.family,
                title=item.title,
                requirement_text=item.requirement_text,
                sprs_weight=item.sprs_weight,
                objective_ids=item.objective_ids,
                evidence_ids=item.evidence_ids,
                interview_ids=item.interview_ids,
                test_ids=item.test_ids,
                sources=item.sources,
            )
            for item in self._sorted_requirements(
                requirements.values()
            )
        )

        compiled_objectives = tuple(
            CompiledObjective(
                framework_id=item.framework_id,
                requirement_id=item.requirement_id,
                objective_id=item.objective_id,
                objective_text=item.objective_text,
                evidence_ids=item.evidence_ids,
                interview_ids=item.interview_ids,
                test_ids=item.test_ids,
                sources=item.sources,
            )
            for item in self._sorted_objectives(
                objectives.values()
            )
        )

        compiled_evidence = tuple(
            CompiledEvidence(
                canonical_id=item.canonical_id,
                title=item.title,
                object_type=item.object_type,
                framework_ids=item.framework_ids,
                requirement_ids=item.requirement_ids,
                objective_ids=item.objective_ids,
                source_methods=(
                    AssessmentMethodKind.EXAMINE,
                ),
                raw_descriptions=item.raw_descriptions,
                sources=item.sources,
            )
            for item in self._sorted_objects(
                evidence.values()
            )
        )

        compiled_interviews = tuple(
            CompiledInterview(
                canonical_id=item.canonical_id,
                title=item.title,
                framework_ids=item.framework_ids,
                requirement_ids=item.requirement_ids,
                objective_ids=item.objective_ids,
                raw_descriptions=item.raw_descriptions,
                sources=item.sources,
            )
            for item in self._sorted_objects(
                interviews.values()
            )
        )

        compiled_tests = tuple(
            CompiledTest(
                canonical_id=item.canonical_id,
                title=item.title,
                framework_ids=item.framework_ids,
                requirement_ids=item.requirement_ids,
                objective_ids=item.objective_ids,
                raw_descriptions=item.raw_descriptions,
                sources=item.sources,
            )
            for item in self._sorted_objects(
                tests.values()
            )
        )

        return CompiledAssessmentKnowledge(
            requirements=compiled_requirements,
            objectives=compiled_objectives,
            evidence=compiled_evidence,
            interviews=compiled_interviews,
            tests=compiled_tests,
        )

    def _compile_method(
        self,
        *,
        row: AssessmentProcedureRow,
        method_type: AssessmentMethodType,
        raw_text: str,
        requirement: _RequirementAccumulator,
        objective: _ObjectiveAccumulator | None,
        target: Dict[str, _ObjectAccumulator],
    ) -> None:
        if not raw_text:
            return

        parsed = self.parser.parse(
            method_type,
            raw_text,
        )

        method_kind = self._method_kind(
            method_type
        )

        for parsed_object in parsed.objects:
            source = self._source(
                row,
                method=method_kind,
            )

            accumulator = target.get(
                parsed_object.canonical_id
            )

            if accumulator is None:
                accumulator = _ObjectAccumulator(
                    canonical_id=(
                        parsed_object.canonical_id
                    ),
                    title=parsed_object.title,
                    object_type=(
                        parsed_object.object_type.value
                    ),
                )

                target[
                    parsed_object.canonical_id
                ] = accumulator

            self._validate_object_consistency(
                accumulator,
                parsed_object,
            )

            self._append_unique(
                accumulator.framework_ids,
                row.framework_id,
            )

            self._append_unique(
                accumulator.requirement_ids,
                row.requirement_id,
            )

            if row.objective_id:
                self._append_unique(
                    accumulator.objective_ids,
                    row.objective_id,
                )

            self._append_unique(
                accumulator.raw_descriptions,
                parsed_object.raw_text,
            )

            self._append_unique(
                accumulator.sources,
                source,
                key=lambda item: item.key,
            )

            if (
                method_type
                == AssessmentMethodType.EXAMINE
            ):
                self._append_unique(
                    requirement.evidence_ids,
                    parsed_object.canonical_id,
                )

                if objective is not None:
                    self._append_unique(
                        objective.evidence_ids,
                        parsed_object.canonical_id,
                    )

            elif (
                method_type
                == AssessmentMethodType.INTERVIEW
            ):
                self._append_unique(
                    requirement.interview_ids,
                    parsed_object.canonical_id,
                )

                if objective is not None:
                    self._append_unique(
                        objective.interview_ids,
                        parsed_object.canonical_id,
                    )

            elif (
                method_type
                == AssessmentMethodType.TEST
            ):
                self._append_unique(
                    requirement.test_ids,
                    parsed_object.canonical_id,
                )

                if objective is not None:
                    self._append_unique(
                        objective.test_ids,
                        parsed_object.canonical_id,
                    )

    def _get_or_create_requirement(
        self,
        requirements: Dict[
            Tuple[str, str],
            _RequirementAccumulator,
        ],
        row: AssessmentProcedureRow,
    ) -> _RequirementAccumulator:
        key = (
            row.framework_id.casefold(),
            row.requirement_id.casefold(),
        )

        existing = requirements.get(
            key
        )

        if existing is None:
            existing = _RequirementAccumulator(
                framework_id=row.framework_id,
                family=row.family,
                requirement_id=row.requirement_id,
                title=row.requirement_title,
                requirement_text=row.requirement_text,
                sprs_weight=row.sprs_weight,
            )

            requirements[key] = existing

            return existing

        self._validate_requirement_consistency(
            existing,
            row,
        )

        if (
            existing.sprs_weight is None
            and row.sprs_weight is not None
        ):
            existing.sprs_weight = (
                row.sprs_weight
            )

        return existing

    def _get_or_create_objective(
        self,
        objectives: Dict[
            Tuple[str, str, str],
            _ObjectiveAccumulator,
        ],
        row: AssessmentProcedureRow,
    ) -> _ObjectiveAccumulator:
        key = (
            row.framework_id.casefold(),
            row.requirement_id.casefold(),
            row.objective_id.casefold(),
        )

        existing = objectives.get(
            key
        )

        if existing is None:
            existing = _ObjectiveAccumulator(
                framework_id=row.framework_id,
                requirement_id=row.requirement_id,
                objective_id=row.objective_id,
                objective_text=row.objective_text,
            )

            objectives[key] = existing

        elif (
            existing.objective_text.casefold()
            != row.objective_text.casefold()
        ):
            raise CatalogCompilerError(
                "Conflicting objective text for "
                f"{row.framework_id}/"
                f"{row.requirement_id}/"
                f"{row.objective_id}."
            )

        self._append_unique(
            existing.sources,
            self._source(
                row,
                method=None,
            ),
            key=lambda item: item.key,
        )

        return existing

    @staticmethod
    def _validate_requirement_consistency(
        existing: _RequirementAccumulator,
        row: AssessmentProcedureRow,
    ) -> None:
        if (
            existing.requirement_text.casefold()
            != row.requirement_text.casefold()
        ):
            raise CatalogCompilerError(
                "Conflicting requirement text for "
                f"{row.framework_id}/"
                f"{row.requirement_id}."
            )

        if (
            existing.family
            and row.family
            and existing.family.casefold()
            != row.family.casefold()
        ):
            raise CatalogCompilerError(
                "Conflicting family for "
                f"{row.framework_id}/"
                f"{row.requirement_id}."
            )

        if (
            existing.title
            and row.requirement_title
            and existing.title.casefold()
            != row.requirement_title.casefold()
        ):
            raise CatalogCompilerError(
                "Conflicting requirement title for "
                f"{row.framework_id}/"
                f"{row.requirement_id}."
            )

        if (
            existing.sprs_weight is not None
            and row.sprs_weight is not None
            and existing.sprs_weight
            != row.sprs_weight
        ):
            raise CatalogCompilerError(
                "Conflicting SPRS weight for "
                f"{row.framework_id}/"
                f"{row.requirement_id}."
            )

    @staticmethod
    def _validate_object_consistency(
        existing: _ObjectAccumulator,
        parsed_object: AssessmentObject,
    ) -> None:
        """
        Validate consistency for objects sharing a canonical ID.

        Minor wording differences in display titles are allowed when
        both parsed objects resolve to the same canonical identifier.

        Object type remains strict because one canonical identifier
        must not represent different assessment object types.
        """

        if (
            existing.title.casefold()
            != parsed_object.title.casefold()
        ):
            pass

        if (
            existing.object_type.casefold()
            != parsed_object.object_type.value.casefold()
        ):
            raise CatalogCompilerError(
                "Canonical object type conflict for "
                f"{parsed_object.canonical_id}: "
                f"{existing.object_type!r} vs "
                f"{parsed_object.object_type.value!r}."
            )

    @staticmethod
    def _source(
        row: AssessmentProcedureRow,
        *,
        method: AssessmentMethodKind | None,
    ) -> SourceReference:
        return SourceReference(
            framework_id=row.framework_id,
            family=row.family,
            requirement_id=row.requirement_id,
            objective_id=row.objective_id,
            method=method,
            source_document=row.source_document,
            source_revision=row.source_revision,
            source_location=row.source_location,
        )

    @staticmethod
    def _method_kind(
        method_type: AssessmentMethodType,
    ) -> AssessmentMethodKind:
        mapping = {
            AssessmentMethodType.EXAMINE:
                AssessmentMethodKind.EXAMINE,

            AssessmentMethodType.INTERVIEW:
                AssessmentMethodKind.INTERVIEW,

            AssessmentMethodType.TEST:
                AssessmentMethodKind.TEST,

            AssessmentMethodType.OBSERVE:
                AssessmentMethodKind.OBSERVE,

            AssessmentMethodType.OTHER:
                AssessmentMethodKind.OTHER,
        }

        return mapping[
            method_type
        ]

    @staticmethod
    def _coerce_row(
        row: AssessmentProcedureRow | Mapping[str, Any],
    ) -> AssessmentProcedureRow:
        if isinstance(
            row,
            AssessmentProcedureRow,
        ):
            return row

        if isinstance(
            row,
            Mapping,
        ):
            return AssessmentProcedureRow.from_mapping(
                row
            )

        raise CatalogCompilerError(
            "CatalogCompiler rows must be "
            "AssessmentProcedureRow instances "
            "or mappings."
        )

    @staticmethod
    def _append_unique(
        values: List[Any],
        value: Any,
        *,
        key=None,
    ) -> None:
        compare = (
            key(value)
            if key
            else (
                value.casefold()
                if isinstance(value, str)
                else value
            )
        )

        for existing in values:
            existing_compare = (
                key(existing)
                if key
                else (
                    existing.casefold()
                    if isinstance(existing, str)
                    else existing
                )
            )

            if existing_compare == compare:
                return

        values.append(
            value
        )

    @staticmethod
    def _sorted_requirements(
        values: Iterable[
            _RequirementAccumulator
        ],
    ) -> List[_RequirementAccumulator]:
        return sorted(
            values,
            key=lambda item: (
                item.framework_id.casefold(),
                item.requirement_id.casefold(),
            ),
        )

    @staticmethod
    def _sorted_objectives(
        values: Iterable[
            _ObjectiveAccumulator
        ],
    ) -> List[_ObjectiveAccumulator]:
        return sorted(
            values,
            key=lambda item: (
                item.framework_id.casefold(),
                item.requirement_id.casefold(),
                item.objective_id.casefold(),
            ),
        )

    @staticmethod
    def _sorted_objects(
        values: Iterable[
            _ObjectAccumulator
        ],
    ) -> List[_ObjectAccumulator]:
        return sorted(
            values,
            key=lambda item: (
                item.canonical_id.casefold()
            ),
        )