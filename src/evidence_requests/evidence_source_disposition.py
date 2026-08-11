from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Tuple


class EvidenceSourceDispositionError(ValueError):
    """Raised when source-disposition data is invalid or ambiguous."""


class EvidenceSourceDispositionKind(str, Enum):
    """Approved reason a generated title does not resolve to collectible evidence."""

    AUTHORITATIVE_REFERENCE = "Authoritative Reference"
    COLLECTION_EXCLUDED = "Collection Excluded"


@dataclass(frozen=True, slots=True)
class EvidenceSourceDisposition:
    """Explicit classification for a non-collected generated source title."""

    source_title: str
    kind: EvidenceSourceDispositionKind
    rationale: str

    def __post_init__(self) -> None:
        source_title = self.source_title.strip()
        rationale = self.rationale.strip()

        if not source_title:
            raise EvidenceSourceDispositionError("source_title cannot be blank.")
        if not rationale:
            raise EvidenceSourceDispositionError("rationale cannot be blank.")

        object.__setattr__(self, "source_title", source_title)
        object.__setattr__(self, "rationale", rationale)


class EvidenceSourceDispositionCatalog:
    """Case-insensitive exact lookup for approved source dispositions."""

    def __init__(
        self,
        dispositions: Iterable[EvidenceSourceDisposition] = (),
    ) -> None:
        self._dispositions: Dict[str, EvidenceSourceDisposition] = {}

        for disposition in dispositions:
            key = disposition.source_title.casefold()
            if key in self._dispositions:
                raise EvidenceSourceDispositionError(
                    f"Duplicate source disposition title: {disposition.source_title!r}."
                )
            self._dispositions[key] = disposition

    def resolve(self, source_title: str) -> EvidenceSourceDisposition | None:
        return self._dispositions.get(str(source_title).strip().casefold())

    @property
    def dispositions(self) -> Tuple[EvidenceSourceDisposition, ...]:
        return tuple(
            sorted(
                self._dispositions.values(),
                key=lambda item: item.source_title.casefold(),
            )
        )


DEFAULT_EVIDENCE_SOURCE_DISPOSITIONS: Tuple[EvidenceSourceDisposition, ...] = (
    EvidenceSourceDisposition(
        "Codes of Federal Regulations",
        EvidenceSourceDispositionKind.AUTHORITATIVE_REFERENCE,
        "External authoritative reference material is not collectible organizational evidence.",
    ),
    EvidenceSourceDisposition(
        "Relevant Codes of Federal Regulations",
        EvidenceSourceDispositionKind.AUTHORITATIVE_REFERENCE,
        "External authoritative reference material is not collectible organizational evidence.",
    ),
    EvidenceSourceDisposition(
        "Collaborative Computing Procedures",
        EvidenceSourceDispositionKind.COLLECTION_EXCLUDED,
        "The owner intentionally excluded this organizational artifact from client collection.",
    ),
    EvidenceSourceDisposition(
        "Other Relevant Documents or Records",
        EvidenceSourceDispositionKind.COLLECTION_EXCLUDED,
        "This open-ended collection instruction is not a stable, independently collectible evidence object.",
    ),
)


def default_evidence_source_disposition_catalog() -> EvidenceSourceDispositionCatalog:
    return EvidenceSourceDispositionCatalog(DEFAULT_EVIDENCE_SOURCE_DISPOSITIONS)
