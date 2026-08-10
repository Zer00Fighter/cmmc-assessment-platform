"""Canonical, framework-independent evidence domain."""

from .evidence_knowledge import EVIDENCE_KNOWLEDGE, VERSION, evidence_knowledge
from .evidence_object import (
    EvidenceArtifactType,
    EvidenceCategory,
    EvidenceObject,
    EvidenceObjectError,
)
from .evidence_resolver import (
    EvidenceResolution,
    EvidenceResolutionStatus,
    EvidenceResolver,
    EvidenceResolverError,
)

__all__ = [
    "EVIDENCE_KNOWLEDGE",
    "VERSION",
    "EvidenceArtifactType",
    "EvidenceCategory",
    "EvidenceObject",
    "EvidenceObjectError",
    "EvidenceResolution",
    "EvidenceResolutionStatus",
    "EvidenceResolver",
    "EvidenceResolverError",
    "evidence_knowledge",
]
