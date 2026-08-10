"""Omni Evidence Body of Knowledge v1.0."""

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


# Chunk 1: governance, planning, risk, and assurance.
EVIDENCE_KNOWLEDGE: Tuple[EvidenceObject, ...] = (
    _evidence(
        "EV-0001",
        "Security Plan",
        aliases=("System Security Plan", "SSP", "Information Security Plan"),
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
        aliases=("Risk Analysis", "Risk Assessment Report"),
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
        aliases=("POA&M", "POAM", "Corrective Action Plan", "Remediation Plan"),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Tracks corrective actions for identified deficiencies.",
    ),
    _evidence(
        "EV-0008",
        "Security Assessment",
        aliases=("Security Assessment Report", "Assessment Results"),
        category=EvidenceCategory.ASSESSMENT,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents evaluation of implemented safeguards.",
    ),
    _evidence(
        "EV-0009",
        "Exception Register",
        aliases=("Policy Exception Register", "Risk Acceptance Register"),
        category=EvidenceCategory.REGISTER,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Tracks approved policy and control exceptions.",
    ),
    _evidence(
        "EV-0010",
        "Control Inventory",
        aliases=("Security Control Inventory", "Safeguard Inventory"),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of implemented security controls.",
    ),
    # Identity and Access.
    _evidence(
        "EV-0011",
        "Account Inventory",
        aliases=(
            "User Account List",
            "Account List",
            "System Account Inventory",
            "List of System Accounts",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of organizational user and system accounts.",
    ),
    _evidence(
        "EV-0012",
        "Privileged Account Inventory",
        aliases=(
            "Privileged Account List",
            "Administrative Account Inventory",
            "Admin Account List",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of accounts assigned elevated or administrative privileges.",
    ),
    _evidence(
        "EV-0013",
        "Access Authorization Records",
        aliases=(
            "Access Approval Records",
            "User Access Authorization Records",
            "Access Authorization Forms",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records approvals for granting or changing access privileges.",
    ),
    _evidence(
        "EV-0014",
        "Access Review Records",
        aliases=(
            "User Access Review Records",
            "Access Recertification Records",
            "Access Certification Records",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records periodic reviews and recertification of access privileges.",
    ),
    _evidence(
        "EV-0015",
        "Authentication Configuration",
        aliases=(
            "Authentication Settings",
            "Authentication System Configuration",
            "Login Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration governing how identities are authenticated.",
    ),
    _evidence(
        "EV-0016",
        "Credential Policy",
        aliases=(
            "Password Policy",
            "Credential Management Policy",
            "Authentication Credential Policy",
        ),
        category=EvidenceCategory.POLICY,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines requirements for credentials throughout their lifecycle.",
    ),
    _evidence(
        "EV-0017",
        "Authenticator Management Procedures",
        aliases=(
            "Authenticator Procedures",
            "Credential Management Procedures",
            "Password Management Procedures",
        ),
        category=EvidenceCategory.PROCEDURE,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents issuance, protection, replacement, and revocation of authenticators.",
    ),
    _evidence(
        "EV-0018",
        "Multi-Factor Authentication Configuration",
        aliases=(
            "MFA Configuration",
            "Two-Factor Authentication Configuration",
            "2FA Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration enforcing the use of multiple authentication factors.",
    ),
    _evidence(
        "EV-0019",
        "Remote Access Configuration",
        aliases=(
            "Remote Access Settings",
            "Remote Connectivity Configuration",
            "VPN Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration controlling and protecting remote system access.",
    ),
    _evidence(
        "EV-0020",
        "Identity Provider Configuration",
        aliases=(
            "IdP Configuration",
            "Identity Management System Configuration",
            "Directory Service Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration of the service that establishes and manages identities.",
    ),
)


def evidence_knowledge() -> Tuple[EvidenceObject, ...]:
    return EVIDENCE_KNOWLEDGE
