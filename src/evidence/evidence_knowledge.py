"""Evidence Knowledge Body of Knowledge v1.0"""

from __future__ import annotations
from typing import Tuple

from src.evidence.evidence_object import (
    EvidenceObject,
    EvidenceCategory,
    EvidenceArtifactType,
)

VERSION = "1.0"


def _evidence(
    evidence_id: str,
    canonical_name: str,
    *,
    aliases: tuple[str, ...],
    category: EvidenceCategory,
    artifact_type: EvidenceArtifactType,
    description: str,
) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        canonical_name=canonical_name,
        aliases=aliases,
        category=category,
        artifact_type=artifact_type,
        description=description,
    )


EVIDENCE_KNOWLEDGE: Tuple[EvidenceObject, ...] = (
    _evidence(
        "EV-0001",
        "Security Plan",
        aliases=("System Security Plan","SSP","Information Security Plan"),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents the organization's security strategy and implementation.",
    ),
    _evidence(
        "EV-0002",
        "Security Policy",
        aliases=("Information Security Policy",),
        category=EvidenceCategory.POLICY,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines management direction and security requirements.",
    ),
    _evidence(
        "EV-0003",
        "Security Standards",
        aliases=("Technical Standards",),
        category=EvidenceCategory.STANDARD,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines mandatory technical and organizational requirements.",
    ),
    _evidence(
        "EV-0004",
        "Security Procedures",
        aliases=("Operating Procedures",),
        category=EvidenceCategory.PROCEDURE,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents repeatable operational security activities.",
    ),
    _evidence(
        "EV-0005",
        "Risk Assessment",
        aliases=("Risk Analysis","Risk Assessment Report"),
        category=EvidenceCategory.ASSESSMENT,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Evaluates threats, vulnerabilities, likelihood and impact.",
    ),
    _evidence(
        "EV-0006",
        "Risk Register",
        aliases=("Enterprise Risk Register",),
        category=EvidenceCategory.REGISTER,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Tracks identified risks and their disposition.",
    ),
    _evidence(
        "EV-0007",
        "Remediation Action Plan",
        aliases=("POA&M","POAM","Corrective Action Plan","Remediation Plan"),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Tracks corrective actions for identified deficiencies.",
    ),
    _evidence(
        "EV-0008",
        "Security Assessment",
        aliases=("Security Assessment Report","Assessment Results"),
        category=EvidenceCategory.ASSESSMENT,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents evaluation of implemented safeguards.",
    ),
    _evidence(
        "EV-0009",
        "Exception Register",
        aliases=("Policy Exception Register","Risk Acceptance Register"),
        category=EvidenceCategory.REGISTER,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Tracks approved policy and control exceptions.",
    ),
    _evidence(
        "EV-0010",
        "Control Inventory",
        aliases=("Security Control Inventory","Safeguard Inventory"),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of implemented security controls.",
    ),
)

def evidence_knowledge() -> Tuple[EvidenceObject,...]:
    return EVIDENCE_KNOWLEDGE