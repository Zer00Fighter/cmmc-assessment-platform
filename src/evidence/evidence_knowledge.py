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
    # Asset Management.
    _evidence(
        "EV-0021",
        "Hardware Asset Inventory",
        aliases=(
            "Hardware Inventory",
            "Device Inventory",
            "System Component Inventory",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of physical technology assets and system components.",
    ),
    _evidence(
        "EV-0022",
        "Software Asset Inventory",
        aliases=(
            "Software Inventory",
            "Application Inventory",
            "Installed Software Inventory",
        ),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of software, applications, and installed components.",
    ),
    _evidence(
        "EV-0023",
        "Information Asset Inventory",
        aliases=("Data Asset Inventory", "Information Inventory", "Data Inventory"),
        category=EvidenceCategory.INVENTORY,
        artifact_type=EvidenceArtifactType.DATASET,
        description="Inventory of organizational information and data assets.",
    ),
    _evidence(
        "EV-0024",
        "Asset Ownership Records",
        aliases=("Asset Assignment Records", "Asset Custodian Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records responsibility and custodianship for organizational assets.",
    ),
    _evidence(
        "EV-0025",
        "Asset Lifecycle Records",
        aliases=(
            "Asset Acquisition Records",
            "Asset Transfer Records",
            "Asset Disposal Records",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records acquisition, assignment, transfer, and disposal of assets.",
    ),
    # Configuration Management.
    _evidence(
        "EV-0026",
        "Configuration Baseline",
        aliases=("System Configuration Baseline", "Approved Configuration Baseline"),
        category=EvidenceCategory.BASELINE,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Defines the approved configuration state for a system or component.",
    ),
    _evidence(
        "EV-0027",
        "Secure Configuration Standard",
        aliases=(
            "Hardening Standard",
            "Security Configuration Standard",
            "Build Standard",
        ),
        category=EvidenceCategory.STANDARD,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Defines requirements for securely configuring systems and components.",
    ),
    _evidence(
        "EV-0028",
        "System Configuration Export",
        aliases=(
            "Configuration Export",
            "System Settings Export",
            "Configuration Snapshot",
        ),
        category=EvidenceCategory.EXPORT,
        artifact_type=EvidenceArtifactType.DATABASE_EXPORT,
        description="Captures the actual configuration state of a system or component.",
    ),
    _evidence(
        "EV-0029",
        "Change Management Records",
        aliases=("Change Records", "Change Tickets", "Change Control Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records authorization, testing, implementation, and review of changes.",
    ),
    _evidence(
        "EV-0030",
        "Configuration Review Records",
        aliases=("Configuration Audit Records", "Baseline Review Records"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records reviews of configurations against approved baselines and standards.",
    ),
    # Network and System Architecture.
    _evidence(
        "EV-0031",
        "Network Diagram",
        aliases=("Network Architecture Diagram", "Network Topology Diagram"),
        category=EvidenceCategory.DIAGRAM,
        artifact_type=EvidenceArtifactType.DIAGRAM,
        description="Depicts network boundaries, components, connections, and trust zones.",
    ),
    _evidence(
        "EV-0032",
        "Data Flow Diagram",
        aliases=("Information Flow Diagram", "Data Movement Diagram"),
        category=EvidenceCategory.DIAGRAM,
        artifact_type=EvidenceArtifactType.DIAGRAM,
        description="Depicts how information moves between processes, systems, and boundaries.",
    ),
    _evidence(
        "EV-0033",
        "System Architecture Documentation",
        aliases=(
            "System Design Documentation",
            "System Architecture",
            "Security Architecture Document",
        ),
        category=EvidenceCategory.DIAGRAM,
        artifact_type=EvidenceArtifactType.DOCUMENT,
        description="Describes system components, interfaces, boundaries, and design.",
    ),
    _evidence(
        "EV-0034",
        "Network Device Configuration",
        aliases=(
            "Router Configuration",
            "Switch Configuration",
            "Network Equipment Configuration",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration of devices that route, switch, or control network traffic.",
    ),
    _evidence(
        "EV-0035",
        "Firewall Configuration",
        aliases=(
            "Firewall Rules",
            "Firewall Rule Set",
            "Firewall Configuration Export",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration enforcing network traffic restrictions and boundary protections.",
    ),
    # Logging and Monitoring.
    _evidence(
        "EV-0036",
        "Audit Logs",
        aliases=("Audit Records", "Security Audit Logs", "System Logs", "Event Logs"),
        category=EvidenceCategory.LOG,
        artifact_type=EvidenceArtifactType.LOG,
        description="Records security-relevant system, application, and user activity.",
    ),
    _evidence(
        "EV-0037",
        "Logging Configuration",
        aliases=(
            "Audit Configuration",
            "Log Collection Configuration",
            "Audit Settings",
        ),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration defining which events are recorded and collected.",
    ),
    _evidence(
        "EV-0038",
        "Log Review Records",
        aliases=(
            "Audit Log Review Records",
            "Log Review Reports",
            "Log Review Tickets",
        ),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records completed reviews and analysis of collected logs.",
    ),
    _evidence(
        "EV-0039",
        "Security Monitoring Configuration",
        aliases=("Monitoring Rules", "Detection Rules", "SIEM Configuration"),
        category=EvidenceCategory.CONFIGURATION,
        artifact_type=EvidenceArtifactType.CONFIGURATION,
        description="Configuration defining security monitoring and detection behavior.",
    ),
    _evidence(
        "EV-0040",
        "Security Alerts",
        aliases=("Monitoring Alerts", "SIEM Alerts", "Detection Alerts"),
        category=EvidenceCategory.RECORD,
        artifact_type=EvidenceArtifactType.RECORD,
        description="Records notifications generated by security monitoring and detection systems.",
    ),
)


def evidence_knowledge() -> Tuple[EvidenceObject, ...]:
    return EVIDENCE_KNOWLEDGE
