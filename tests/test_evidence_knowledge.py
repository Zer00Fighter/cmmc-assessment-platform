from __future__ import annotations

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE, evidence_knowledge
from src.evidence.evidence_object import EvidenceCategory

EXPECTED_NAMES = (
    "Security Plan",
    "Security Policy",
    "Security Standards",
    "Security Procedures",
    "Risk Assessment",
    "Risk Register",
    "Remediation Action Plan",
    "Security Assessment",
    "Exception Register",
    "Control Inventory",
    "Account Inventory",
    "Privileged Account Inventory",
    "Access Authorization Records",
    "Access Review Records",
    "Authentication Configuration",
    "Credential Policy",
    "Authenticator Management Procedures",
    "Multi-Factor Authentication Configuration",
    "Remote Access Configuration",
    "Identity Provider Configuration",
    "Hardware Asset Inventory",
    "Software Asset Inventory",
    "Information Asset Inventory",
    "Asset Ownership Records",
    "Asset Lifecycle Records",
    "Configuration Baseline",
    "Secure Configuration Standard",
    "System Configuration Export",
    "Change Management Records",
    "Configuration Review Records",
    "Network Diagram",
    "Data Flow Diagram",
    "System Architecture Documentation",
    "Network Device Configuration",
    "Firewall Configuration",
    "Audit Logs",
    "Logging Configuration",
    "Log Review Records",
    "Security Monitoring Configuration",
    "Security Alerts",
)


def test_knowledge_contains_the_approved_first_forty_objects() -> None:
    assert tuple(item.evidence_id for item in EVIDENCE_KNOWLEDGE) == tuple(
        f"EV-{index:04d}" for index in range(1, 41)
    )
    assert tuple(item.canonical_name for item in EVIDENCE_KNOWLEDGE) == EXPECTED_NAMES


def test_ids_names_and_aliases_are_unambiguous() -> None:
    ids = [item.evidence_id.casefold() for item in EVIDENCE_KNOWLEDGE]
    names = [name.casefold() for item in EVIDENCE_KNOWLEDGE for name in item.names]

    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))


def test_credential_policy_preserves_password_policy_as_an_alias() -> None:
    credential_policy = EVIDENCE_KNOWLEDGE[15]

    assert credential_policy.canonical_name == "Credential Policy"
    assert "Password Policy" in credential_policy.aliases


def test_identity_and_access_objects_preserve_cross_framework_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "List of System Accounts" in aliases_by_name["Account Inventory"]
    assert "Privileged Account List" in aliases_by_name["Privileged Account Inventory"]
    assert "Access Approval Records" in aliases_by_name["Access Authorization Records"]
    assert "Access Recertification Records" in aliases_by_name["Access Review Records"]
    assert "Password Policy" in aliases_by_name["Credential Policy"]
    assert (
        "MFA Configuration"
        in aliases_by_name["Multi-Factor Authentication Configuration"]
    )
    assert "VPN Configuration" in aliases_by_name["Remote Access Configuration"]
    assert "IdP Configuration" in aliases_by_name["Identity Provider Configuration"]


def test_sprint_3_5_objects_preserve_framework_agnostic_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "Device Inventory" in aliases_by_name["Hardware Asset Inventory"]
    assert "Application Inventory" in aliases_by_name["Software Asset Inventory"]
    assert "Hardening Standard" in aliases_by_name["Secure Configuration Standard"]
    assert "Change Tickets" in aliases_by_name["Change Management Records"]
    assert "Network Topology Diagram" in aliases_by_name["Network Diagram"]
    assert (
        "System Design Documentation"
        in aliases_by_name["System Architecture Documentation"]
    )
    assert "Firewall Rules" in aliases_by_name["Firewall Configuration"]
    assert "System Logs" in aliases_by_name["Audit Logs"]
    assert "SIEM Configuration" in aliases_by_name["Security Monitoring Configuration"]
    assert "SIEM Alerts" in aliases_by_name["Security Alerts"]


def test_remediation_plan_is_not_a_poam_category() -> None:
    remediation_plan = EVIDENCE_KNOWLEDGE[6]

    assert remediation_plan.category == EvidenceCategory.PLAN
    assert "POA&M" in remediation_plan.aliases
    assert not hasattr(EvidenceCategory, "POAM")


def test_knowledge_accessor_returns_the_immutable_catalog() -> None:
    assert evidence_knowledge() is EVIDENCE_KNOWLEDGE
