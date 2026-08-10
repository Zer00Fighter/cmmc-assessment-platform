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
    # Chunk 2: identity, assets, architecture, and configuration.
    _evidence(
        "EV-0011",
        "Access Control Policy",
        aliases=("Access Control Policy and Procedures",),
        category=EvidenceCategory.POLICY,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines requirements for granting, reviewing, and revoking access.",
    ),
    _evidence(
        "EV-0012",
        "Account Inventory",
        aliases=(
            "System and Privileged Account Inventory",
            "List of System Accounts",
            "Privileged Account List",
            "Service Account List",
            "Shared Account List",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of user, privileged, service, and shared accounts.",
    ),
    _evidence(
        "EV-0013",
        "Account Management Procedures",
        aliases=(
            "Account Management Documentation",
            "Account Management Process",
            "Account Management Records",
        ),
        category=EvidenceCategory.PROCEDURE,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents the lifecycle for creating, reviewing, and disabling accounts.",
    ),
    _evidence(
        "EV-0014",
        "Asset Inventory",
        aliases=(
            "Hardware and System Component Inventory",
            "Hardware Inventory",
            "System Component Inventory",
            "Information System Component Inventory",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of organizational technology assets and system components.",
    ),
    _evidence(
        "EV-0015",
        "Software Inventory",
        aliases=(
            "Software and Application Inventory",
            "Application Inventory",
            "Installed Software Inventory",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of approved software, applications, and installed components.",
    ),
    _evidence(
        "EV-0016",
        "Configuration Baseline",
        aliases=(
            "System Configuration Baseline",
            "System Configuration Baseline and Settings",
            "System Configuration Settings and Associated Documentation",
            "Security Configuration Settings",
        ),
        category=EvidenceCategory.BASELINE,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Defines approved and securely configured system settings.",
    ),
    _evidence(
        "EV-0017",
        "Change Management Records",
        aliases=("Change Control Records", "Configuration Change Control Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records the authorization, testing, and implementation of changes.",
    ),
    _evidence(
        "EV-0018",
        "Network Diagram",
        aliases=("Network Architecture Diagram", "Network Topology Diagram"),
        category=EvidenceCategory.DIAGRAM,
        artifact_type=EvidenceArtifactType.DIAGRAM,
        description="Depicts network boundaries, components, connections, and trust zones.",
    ),
    _evidence(
        "EV-0019",
        "System Architecture Documentation",
        aliases=(
            "System Design and Architecture Documentation",
            "System Design Documentation",
            "System Architecture",
        ),
        category=EvidenceCategory.DIAGRAM,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Describes system components, interfaces, boundaries, and design.",
    ),
    _evidence(
        "EV-0020",
        "Firewall Configuration",
        aliases=(
            "Firewall Rules",
            "Firewall Rule Set",
            "Firewall Configuration Export",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Documents enforced firewall rules and network traffic restrictions.",
    ),
    # Chunk 3: monitoring, response, personnel, and operations.
    _evidence(
        "EV-0021",
        "Audit Logs",
        aliases=(
            "System Audit Logs and Records",
            "Audit Records",
            "Security Audit Logs",
            "System Logs",
        ),
        category=EvidenceCategory.LOG,
        artifact_type=EvidenceArtifactType.LOG,
        description="Records security-relevant system and user activity.",
    ),
    _evidence(
        "EV-0022",
        "Incident Response Plan",
        aliases=(
            "Incident Response Plan and Procedures",
            "Cybersecurity Incident Response Plan",
        ),
        category=EvidenceCategory.PLAN,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines responsibilities and procedures for responding to incidents.",
    ),
    _evidence(
        "EV-0023",
        "Incident Records",
        aliases=("Security Incident Records", "Incident Tickets", "Incident Reports"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records detected incidents, response actions, and outcomes.",
    ),
    _evidence(
        "EV-0024",
        "Vulnerability Scan Report",
        aliases=("Vulnerability Scan Results", "Vulnerability Assessment Report"),
        category=EvidenceCategory.REPORT,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Reports identified technical vulnerabilities and scan findings.",
    ),
    _evidence(
        "EV-0025",
        "Patch Management Records",
        aliases=("Patch Records", "Patch Deployment Records", "Update Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records the evaluation, approval, deployment, and verification of patches.",
    ),
    _evidence(
        "EV-0026",
        "Security Training Records",
        aliases=(
            "Security Awareness and Training Records",
            "Security Awareness Training Records",
            "Training Records",
        ),
        category=EvidenceCategory.TRAINING,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records security awareness and role-based training completion.",
    ),
    _evidence(
        "EV-0027",
        "Personnel Screening Records",
        aliases=(
            "Personnel Screening and Authorization Records",
            "Personnel Security Records",
            "Personnel Authorization Records",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records personnel screening, authorization, and access eligibility.",
    ),
    _evidence(
        "EV-0028",
        "Media Inventory",
        aliases=(
            "Media Inventory and Tracking Records",
            "Media Tracking Records",
            "Media Records",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory and custody history of physical and digital media.",
    ),
    _evidence(
        "EV-0029",
        "Maintenance Records",
        aliases=("Maintenance Records and Procedures", "System Maintenance Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records authorized system maintenance and related activities.",
    ),
    _evidence(
        "EV-0030",
        "Third-Party Agreement",
        aliases=(
            "Third-Party Agreements",
            "Supplier Agreement",
            "Service Provider Agreement",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Documents security obligations agreed with external parties.",
    ),
)


def evidence_knowledge() -> Tuple[EvidenceObject, ...]:
    return EVIDENCE_KNOWLEDGE
