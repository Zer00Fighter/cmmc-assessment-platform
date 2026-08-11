from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject


class EvidenceSourceMappingError(ValueError):
    """Raised when curated source mapping data is invalid or ambiguous."""


@dataclass(frozen=True, slots=True)
class EvidenceSourceMapping:
    """Exact mapping from one source phrase to one or more Evidence Objects."""

    source_title: str
    evidence_ids: Tuple[str, ...]
    rationale: str = ""

    def __post_init__(self) -> None:
        source_title = self.source_title.strip()
        evidence_ids = tuple(
            dict.fromkeys(value.strip() for value in self.evidence_ids if value.strip())
        )

        if not source_title:
            raise EvidenceSourceMappingError("source_title cannot be blank.")
        if not evidence_ids:
            raise EvidenceSourceMappingError("evidence_ids cannot be empty.")

        object.__setattr__(self, "source_title", source_title)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "rationale", self.rationale.strip())


class EvidenceSourceMappingCatalog:
    """Case-insensitive exact lookup for curated, potentially compound mappings."""

    def __init__(
        self,
        mappings: Iterable[EvidenceSourceMapping] = (),
        *,
        evidence_objects: Iterable[EvidenceObject] = EVIDENCE_KNOWLEDGE,
    ) -> None:
        objects = tuple(evidence_objects)
        self._evidence_by_id: Dict[str, EvidenceObject] = {
            item.evidence_id.casefold(): item for item in objects
        }
        self._mappings: Dict[str, EvidenceSourceMapping] = {}

        for mapping in mappings:
            key = mapping.source_title.casefold()
            if key in self._mappings:
                raise EvidenceSourceMappingError(
                    f"Duplicate source mapping title: {mapping.source_title!r}."
                )
            unknown_ids = [
                evidence_id
                for evidence_id in mapping.evidence_ids
                if evidence_id.casefold() not in self._evidence_by_id
            ]
            if unknown_ids:
                raise EvidenceSourceMappingError(
                    f"Unknown Evidence Object IDs for {mapping.source_title!r}: "
                    f"{unknown_ids!r}."
                )
            self._mappings[key] = mapping

    def resolve(self, source_title: str) -> Tuple[EvidenceObject, ...]:
        mapping = self._mappings.get(str(source_title).strip().casefold())
        if mapping is None:
            return ()
        return tuple(
            self._evidence_by_id[evidence_id.casefold()]
            for evidence_id in mapping.evidence_ids
        )

    @property
    def mappings(self) -> Tuple[EvidenceSourceMapping, ...]:
        return tuple(
            sorted(
                self._mappings.values(), key=lambda item: item.source_title.casefold()
            )
        )


DEFAULT_EVIDENCE_SOURCE_MAPPINGS: Tuple[EvidenceSourceMapping, ...] = (
    EvidenceSourceMapping(
        "Cryptographic Mechanisms and Associated Configuration Documentation",
        ("EV-0070", "EV-0073"),
        "The source phrase requests both the mechanism inventory and its configuration.",
    ),
    EvidenceSourceMapping(
        "Encryption Mechanisms and Associated Configuration Documentation",
        ("EV-0070", "EV-0073"),
        "Encryption mechanism and configuration evidence are independently reusable.",
    ),
    EvidenceSourceMapping(
        "Notifications or Records of Recently Transferred Separated or Terminated Employees",
        ("EV-0058", "EV-0059"),
        "The source combines personnel transfer and termination records.",
    ),
    EvidenceSourceMapping(
        "Patch and Vulnerability Management Records",
        ("EV-0077", "EV-0078"),
        "Vulnerability remediation and patch deployment records can exist independently.",
    ),
    EvidenceSourceMapping(
        "Records of Personnel Transfer and Termination Actions",
        ("EV-0058", "EV-0059"),
        "The source combines personnel transfer and termination records.",
    ),
    EvidenceSourceMapping(
        "Security Plan System Design Documentation",
        ("EV-0001", "EV-0033"),
        "A security plan and system design documentation are distinct artifacts.",
    ),
    EvidenceSourceMapping(
        "System Architecture and Configuration Documentation",
        ("EV-0033", "EV-0028"),
        "Architecture documentation and actual configuration evidence are distinct.",
    ),
    EvidenceSourceMapping(
        "System Configuration Settings and Associated Documentation System Audit Logs and Records",
        ("EV-0028", "EV-0036"),
        "The source combines system configuration evidence with audit logs.",
    ),
)


def default_evidence_source_mapping_catalog() -> EvidenceSourceMappingCatalog:
    return EvidenceSourceMappingCatalog(DEFAULT_EVIDENCE_SOURCE_MAPPINGS)
