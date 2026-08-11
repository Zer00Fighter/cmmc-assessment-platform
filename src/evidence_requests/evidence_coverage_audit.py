from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Iterable, Mapping, Tuple

from src.assessment_knowledge.models import CompiledAssessmentKnowledge
from src.evidence.evidence_resolver import EvidenceResolver
from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
)


class EvidenceCoverageAuditError(ValueError):
    """Raised when generated evidence cannot be audited deterministically."""


class EvidenceCoverageMatchKind(str, Enum):
    """How a generated evidence title maps to the canonical EBK."""

    CANONICAL = "Canonical"
    ALIAS = "Alias"
    UNRESOLVED = "Unresolved"


@dataclass(frozen=True, slots=True)
class EvidenceCoverageEntry:
    """Traceable EBK resolution result for one generated DRL request."""

    request_id: str
    requested_item: str
    match_kind: EvidenceCoverageMatchKind
    evidence_id: str | None
    canonical_name: str
    matched_name: str
    framework_ids: Tuple[str, ...]
    control_ids: Tuple[str, ...]
    control_families: Tuple[str, ...]
    objective_ids: Tuple[str, ...]
    evidence_type: str

    @property
    def resolved(self) -> bool:
        return self.evidence_id is not None


@dataclass(frozen=True, slots=True)
class EvidenceCoverageGroup:
    """Resolution coverage for a control family or evidence type."""

    name: str
    total: int
    resolved: int
    unresolved: int

    @property
    def coverage_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.resolved / self.total * 100, 2)


@dataclass(frozen=True, slots=True)
class EvidenceCoverageReport:
    """Deterministic coverage report for a generated DRL."""

    framework_id: str
    entries: Tuple[EvidenceCoverageEntry, ...]
    by_control_family: Tuple[EvidenceCoverageGroup, ...]
    by_evidence_type: Tuple[EvidenceCoverageGroup, ...]

    @property
    def total_requests(self) -> int:
        return len(self.entries)

    @property
    def canonical_matches(self) -> int:
        return sum(
            entry.match_kind == EvidenceCoverageMatchKind.CANONICAL
            for entry in self.entries
        )

    @property
    def alias_matches(self) -> int:
        return sum(
            entry.match_kind == EvidenceCoverageMatchKind.ALIAS
            for entry in self.entries
        )

    @property
    def unresolved(self) -> int:
        return sum(not entry.resolved for entry in self.entries)

    @property
    def resolved(self) -> int:
        return self.total_requests - self.unresolved

    @property
    def coverage_percent(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.resolved / self.total_requests * 100, 2)

    @property
    def objective_traced_requests(self) -> int:
        return sum(bool(entry.objective_ids) for entry in self.entries)

    @property
    def missing_objective_trace(self) -> int:
        return self.total_requests - self.objective_traced_requests

    @property
    def objective_trace_percent(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(
            self.objective_traced_requests / self.total_requests * 100,
            2,
        )

    @property
    def missing_objective_titles(self) -> Tuple[str, ...]:
        titles = {
            entry.requested_item.casefold(): entry.requested_item
            for entry in self.entries
            if not entry.objective_ids
        }
        return tuple(sorted(titles.values(), key=str.casefold))

    @property
    def unresolved_titles(self) -> Tuple[str, ...]:
        titles = {
            entry.requested_item.casefold(): entry.requested_item
            for entry in self.entries
            if not entry.resolved
        }
        return tuple(sorted(titles.values(), key=str.casefold))


class EvidenceCoverageAuditor:
    """Audit generated DRL titles against canonical Evidence Knowledge."""

    def __init__(self, resolver: EvidenceResolver | None = None) -> None:
        self.resolver = resolver or EvidenceResolver()

    def audit(
        self,
        collection: DocumentationRequestCollection,
        *,
        knowledge: CompiledAssessmentKnowledge | None = None,
    ) -> EvidenceCoverageReport:
        objective_index = self._objective_ids_by_title(
            knowledge,
            framework_id=collection.framework_id,
        )
        entries = tuple(
            self._entry(request, objective_index=objective_index)
            for request in collection.requests
        )

        return EvidenceCoverageReport(
            framework_id=collection.framework_id,
            entries=entries,
            by_control_family=self._groups(
                entries,
                values=lambda entry: entry.control_families,
            ),
            by_evidence_type=self._groups(
                entries,
                values=lambda entry: (entry.evidence_type,),
            ),
        )

    def _entry(
        self,
        request: DocumentationRequest,
        *,
        objective_index: Mapping[str, Tuple[str, ...]],
    ) -> EvidenceCoverageEntry:
        resolution = self.resolver.resolve(request.requested_item)
        evidence = resolution.evidence

        if evidence is None:
            match_kind = EvidenceCoverageMatchKind.UNRESOLVED
            evidence_id = None
            canonical_name = ""
        else:
            match_kind = (
                EvidenceCoverageMatchKind.CANONICAL
                if request.requested_item.casefold()
                == evidence.canonical_name.casefold()
                else EvidenceCoverageMatchKind.ALIAS
            )
            evidence_id = evidence.evidence_id
            canonical_name = evidence.canonical_name

        return EvidenceCoverageEntry(
            request_id=request.request_id,
            requested_item=request.requested_item,
            match_kind=match_kind,
            evidence_id=evidence_id,
            canonical_name=canonical_name,
            matched_name=resolution.matched_name,
            framework_ids=request.framework_ids,
            control_ids=request.control_ids,
            control_families=request.control_families,
            objective_ids=objective_index.get(
                request.requested_item.casefold(),
                (),
            ),
            evidence_type=request.evidence_type.value,
        )

    @staticmethod
    def _objective_ids_by_title(
        knowledge: CompiledAssessmentKnowledge | None,
        *,
        framework_id: str,
    ) -> Dict[str, Tuple[str, ...]]:
        if knowledge is None:
            return {}

        framework_key = framework_id.casefold()
        result: Dict[str, Tuple[str, ...]] = {}

        for evidence in knowledge.evidence:
            if not any(
                value.casefold() == framework_key for value in evidence.framework_ids
            ):
                continue

            key = evidence.title.casefold()
            objective_ids = tuple(evidence.objective_ids)
            existing = result.get(key)
            if existing is not None and existing != objective_ids:
                raise EvidenceCoverageAuditError(
                    "Generated evidence title has ambiguous objective traceability: "
                    f"{evidence.title!r}."
                )
            result[key] = objective_ids

        return result

    @staticmethod
    def _groups(
        entries: Iterable[EvidenceCoverageEntry],
        *,
        values: Callable[[EvidenceCoverageEntry], Tuple[str, ...]],
    ) -> Tuple[EvidenceCoverageGroup, ...]:
        totals: Dict[str, Tuple[str, int, int]] = {}

        for entry in entries:
            for value in values(entry):
                key = value.casefold()
                name, total, resolved = totals.get(key, (value, 0, 0))
                totals[key] = (
                    name,
                    total + 1,
                    resolved + int(entry.resolved),
                )

        return tuple(
            EvidenceCoverageGroup(
                name=group[0],
                total=group[1],
                resolved=group[2],
                unresolved=group[1] - group[2],
            )
            for _, group in sorted(totals.items())
        )
