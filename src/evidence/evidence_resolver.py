from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Tuple

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject


class EvidenceResolutionStatus(str, Enum):
    """Outcome of a deterministic Evidence Object resolution."""

    EXACT = "Exact"
    NORMALIZED = "Normalized"
    UNRESOLVED = "Unresolved"


@dataclass(frozen=True, slots=True)
class EvidenceResolution:
    """Traceable result for one source evidence name."""

    source_name: str
    status: EvidenceResolutionStatus
    evidence: EvidenceObject | None = None
    matched_name: str = ""

    @property
    def resolved(self) -> bool:
        return self.evidence is not None

    @property
    def evidence_id(self) -> str | None:
        return self.evidence.evidence_id if self.evidence else None


class EvidenceResolverError(ValueError):
    """Raised when resolver knowledge contains ambiguous names."""


class EvidenceResolver:
    """Resolve source wording without fuzzy or semantic guessing."""

    def __init__(
        self,
        objects: Iterable[EvidenceObject] = EVIDENCE_KNOWLEDGE,
    ) -> None:
        self._objects: Tuple[EvidenceObject, ...] = tuple(objects)
        self._exact: Dict[str, tuple[EvidenceObject, str]] = {}
        self._normalized: Dict[str, tuple[EvidenceObject, str]] = {}

        for evidence in self._objects:
            for name in evidence.names:
                self._register(self._exact, name.casefold(), evidence, name)
                self._register(self._normalized, self.normalize(name), evidence, name)

    def resolve(self, source_name: str) -> EvidenceResolution:
        source = str(source_name).strip()
        if not source:
            return EvidenceResolution(source, EvidenceResolutionStatus.UNRESOLVED)

        exact = self._exact.get(source.casefold())
        if exact is not None:
            evidence, matched_name = exact
            return EvidenceResolution(
                source, EvidenceResolutionStatus.EXACT, evidence, matched_name
            )

        normalized = self._normalized.get(self.normalize(source))
        if normalized is not None:
            evidence, matched_name = normalized
            return EvidenceResolution(
                source, EvidenceResolutionStatus.NORMALIZED, evidence, matched_name
            )

        return EvidenceResolution(source, EvidenceResolutionStatus.UNRESOLVED)

    def resolve_many(
        self, source_names: Iterable[str]
    ) -> Tuple[EvidenceResolution, ...]:
        return tuple(self.resolve(name) for name in source_names)

    @staticmethod
    def normalize(value: str) -> str:
        text = str(value).casefold().replace("&", " and ")
        return " ".join(re.findall(r"[a-z0-9]+", text))

    @staticmethod
    def _register(
        index: Dict[str, tuple[EvidenceObject, str]],
        key: str,
        evidence: EvidenceObject,
        name: str,
    ) -> None:
        if not key:
            return
        existing = index.get(key)
        if existing is not None and existing[0] != evidence:
            raise EvidenceResolverError(
                "Ambiguous Evidence Object name after normalization: " f"{name!r}."
            )
        index[key] = (evidence, name)
