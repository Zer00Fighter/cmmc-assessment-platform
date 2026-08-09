from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class EvidenceObjectError(ValueError):
    """Raised when Evidence Object data is invalid."""


class EvidenceCategory(str, Enum):
    """
    Logical category of evidence.

    Evidence categories are framework-independent and describe
    what kind of evidence the object represents.
    """

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    PLAN = "Plan"
    STANDARD = "Standard"
    BASELINE = "Baseline"
    CONFIGURATION = "Configuration"
    INVENTORY = "Inventory"
    DIAGRAM = "Diagram"
    LOG = "Log"
    REPORT = "Report"
    RECORD = "Record"
    LIST = "List"
    TRAINING = "Training"
    ASSESSMENT = "Assessment"
    SCREENSHOT = "Screenshot"
    EXPORT = "Export"
    POAM = "POA&M"
    OTHER = "Other"


class EvidenceArtifactType(str, Enum):
    """
    Physical or technical form of an evidence artifact.

    This is intentionally separate from EvidenceCategory.

    Example:

        System Security Plan
            category      = PLAN
            artifact_type = DOCUMENT

        Firewall Configuration
            category      = CONFIGURATION
            artifact_type = CONFIGURATION

        Audit Logs
            category      = LOG
            artifact_type = DATASET
    """

    DOCUMENT = "Document"
    RECORD = "Record"
    DATASET = "Dataset"
    CONFIGURATION = "Configuration"
    LOG = "Log"
    DIAGRAM = "Diagram"
    IMAGE = "Image"
    SPREADSHEET = "Spreadsheet"
    DATABASE_EXPORT = "Database Export"
    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class EvidenceObject:
    """
    Framework-independent logical evidence object.

    An EvidenceObject represents a real business, operational,
    technical, or governance artifact that may be used as evidence
    during one or more assessments.

    Evidence objects intentionally do not contain:
      - framework mappings;
      - control mappings;
      - assessment objectives;
      - owners;
      - collection status;
      - DRL request information;
      - optimization rules.

    Those concepts belong to other layers of the platform.
    """

    evidence_id: str

    canonical_name: str

    aliases: Tuple[str, ...] = ()

    category: EvidenceCategory = (
        EvidenceCategory.OTHER
    )

    artifact_type: EvidenceArtifactType = (
        EvidenceArtifactType.OTHER
    )

    description: str = ""

    def __post_init__(self) -> None:
        evidence_id = self.evidence_id.strip()

        canonical_name = (
            self.canonical_name.strip()
        )

        description = self.description.strip()

        if not evidence_id:
            raise EvidenceObjectError(
                "EvidenceObject.evidence_id "
                "cannot be blank."
            )

        if not canonical_name:
            raise EvidenceObjectError(
                "EvidenceObject.canonical_name "
                "cannot be blank."
            )

        normalized_aliases = (
            self._normalize_aliases(
                self.aliases,
                canonical_name=canonical_name,
            )
        )

        object.__setattr__(
            self,
            "evidence_id",
            evidence_id,
        )

        object.__setattr__(
            self,
            "canonical_name",
            canonical_name,
        )

        object.__setattr__(
            self,
            "aliases",
            normalized_aliases,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

    @property
    def names(self) -> Tuple[str, ...]:
        """
        All recognized names for this evidence object.

        The canonical name is always first.
        """

        return (
            self.canonical_name,
            *self.aliases,
        )

    @property
    def key(self) -> str:
        """
        Case-insensitive identity key.
        """

        return self.evidence_id.casefold()

    def matches_name(
        self,
        value: str,
    ) -> bool:
        """
        Return True when a value matches the canonical name
        or one of the object's aliases.

        Matching is case-insensitive and ignores surrounding
        whitespace.
        """

        candidate = value.strip().casefold()

        if not candidate:
            return False

        return any(
            name.casefold() == candidate
            for name in self.names
        )

    @staticmethod
    def _normalize_aliases(
        aliases: Tuple[str, ...],
        *,
        canonical_name: str,
    ) -> Tuple[str, ...]:
        """
        Normalize and deduplicate aliases.

        The canonical name itself is not repeated in aliases.
        """

        result = []

        seen = {
            canonical_name.casefold()
        }

        for alias in aliases:
            normalized = str(
                alias
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