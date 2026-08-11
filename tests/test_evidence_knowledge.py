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
    "Incident Response Plan",
    "Incident Response Procedures",
    "Incident Records",
    "Incident Response Exercise Records",
    "Incident Communication Records",
    "Business Continuity Plan",
    "Disaster Recovery Plan",
    "Backup Configuration",
    "Backup Records",
    "Recovery Test Records",
    "Physical Security Plan",
    "Physical Access Authorization Records",
    "Physical Access Logs",
    "Visitor Records",
    "Physical Security Monitoring Records",
    "Personnel Screening Records",
    "Personnel Security Agreements",
    "Personnel Transfer Records",
    "Personnel Termination Records",
    "Security Training Records",
    "Third-Party Inventory",
    "Third-Party Risk Assessment",
    "Third-Party Due Diligence Records",
    "Third-Party Agreements",
    "Third-Party Security Requirements",
    "Third-Party Monitoring Records",
    "Third-Party Review Records",
    "Cryptographic Policy",
    "Cryptographic Standards",
    "Cryptographic Asset Inventory",
    "Key Management Procedures",
    "Key Management Records",
    "Cryptographic Configuration",
    "Certificate Inventory",
    "Security Operations Procedures",
    "Vulnerability Scan Report",
    "Vulnerability Management Records",
    "Patch Management Records",
    "Malware Protection Configuration",
    "Security Operations Reports",
    "Access Control Policy",
    "Access Control Procedures",
    "Access Control List",
    "Account Management Procedures",
    "Credential Inventory",
    "Authorized Personnel List",
    "Configuration Management Plan",
    "Configuration Management Policy",
    "Configuration Management Procedures",
    "Security Impact Analysis",
    "Media Protection Policy",
    "Media Protection Procedures",
    "Media Inventory",
    "Media Sanitization Records",
    "Media Transport Records",
    "Maintenance Policy",
    "Maintenance Procedures",
    "Maintenance Records",
    "Maintenance Tool Inventory",
    "Maintenance Tool Inspection Records",
    "Mobile Device Access Procedures",
    "Account Management Review Records",
    "Configuration Change Control Meeting Records",
    "Alternate Work Site Security Procedures",
    "Security Analysis Tool Inventory",
    "Security Analysis Results",
    "Media Handling and Sanitization Policy",
    "Application Segmentation and Isolation Procedures",
    "Alternate Work Site Security Assessment",
    "Audit and Accountability Policy",
    "Audit Logging Tool Inventory",
    "Audit Logging Procedures",
    "Boundary Protection Procedures",
    "Contingency Plan",
    "Contingency Plan Testing Procedures",
    "Contingency Planning Policy",
    "Continuous Monitoring Strategy",
    "Cryptographic Module Validation Certificates",
    "Cryptographic Protection Procedures",
    "Controlled Area Register",
    "Diagnostic Records",
    "Separation of Duties Procedures",
    "System Use Banner Policy",
    "Facility Diagram",
    "Vulnerability Remediation Procedures",
    "Identity and Access Management Policy",
    "Identity and Access Management Procedures",
    "Incident Response Policy",
    "Incident Response Exercise Plan",
    "Incident Response Exercise Materials",
    "Incident Response Exercise Procedures",
    "Incident Response Training Materials",
    "Incident Response Training Procedures",
    "Security Architecture Policy",
    "Security Architecture Procedures",
    "Insider Threat Policy",
    "Insider Threat Procedures",
    "Asset Management Policy",
    "Asset Management Procedures",
    "Physical Security Policy",
    "Public Communications Procedures",
    "Malware Protection Procedures",
)


def test_knowledge_contains_the_approved_first_one_hundred_forty_two_objects() -> None:
    assert tuple(item.evidence_id for item in EVIDENCE_KNOWLEDGE) == tuple(
        f"EV-{index:04d}" for index in range(1, 143)
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


def test_sprint_3_6_objects_preserve_framework_agnostic_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "IR Plan" in aliases_by_name["Incident Response Plan"]
    assert "Incident Tickets" in aliases_by_name["Incident Records"]
    assert (
        "Tabletop Exercise Results"
        in aliases_by_name["Incident Response Exercise Records"]
    )
    assert "BCP" in aliases_by_name["Business Continuity Plan"]
    assert "DRP" in aliases_by_name["Disaster Recovery Plan"]
    assert "Backup Logs" in aliases_by_name["Backup Records"]
    assert "Badge Access Logs" in aliases_by_name["Physical Access Logs"]
    assert "Visitor Logs" in aliases_by_name["Visitor Records"]
    assert "Background Check Records" in aliases_by_name["Personnel Screening Records"]
    assert "Offboarding Records" in aliases_by_name["Personnel Termination Records"]
    assert (
        "Security Awareness Training Records"
        in aliases_by_name["Security Training Records"]
    )


def test_sprint_3_7_objects_preserve_framework_agnostic_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "Vendor Inventory" in aliases_by_name["Third-Party Inventory"]
    assert "Vendor Risk Assessment" in aliases_by_name["Third-Party Risk Assessment"]
    assert (
        "Third-Party Security Questionnaire"
        in aliases_by_name["Third-Party Due Diligence Records"]
    )
    assert "Service Provider Agreements" in aliases_by_name["Third-Party Agreements"]
    assert "Encryption Policy" in aliases_by_name["Cryptographic Policy"]
    assert "Key Rotation Records" in aliases_by_name["Key Management Records"]
    assert "TLS Certificate Inventory" in aliases_by_name["Certificate Inventory"]
    assert "SOC Procedures" in aliases_by_name["Security Operations Procedures"]
    assert "Vulnerability Scan Results" in aliases_by_name["Vulnerability Scan Report"]
    assert "Patch Deployment Records" in aliases_by_name["Patch Management Records"]
    assert (
        "Endpoint Protection Configuration"
        in aliases_by_name["Malware Protection Configuration"]
    )


def test_sprint_3_9_objects_preserve_framework_agnostic_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "Logical Access Control Policy" in aliases_by_name["Access Control Policy"]
    assert "ACL" in aliases_by_name["Access Control List"]
    assert "Access Credentials" in aliases_by_name["Credential Inventory"]
    assert "CM Plan" in aliases_by_name["Configuration Management Plan"]
    assert (
        "System Media Protection Policy" in aliases_by_name["Media Protection Policy"]
    )
    assert "System Media" in aliases_by_name["Media Inventory"]
    assert (
        "Equipment Sanitization Records"
        in aliases_by_name["Media Sanitization Records"]
    )
    assert "System Maintenance Policy" in aliases_by_name["Maintenance Policy"]
    assert "Maintenance Logs" in aliases_by_name["Maintenance Records"]


def test_sprint_3_10_batch_1_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert (
        "Mobile Device Security Procedures"
        in aliases_by_name["Mobile Device Access Procedures"]
    )
    assert (
        "Account Management Compliance Reviews"
        in aliases_by_name["Account Management Review Records"]
    )
    assert "Security Analysis Outputs" in aliases_by_name["Security Analysis Results"]
    assert (
        "Media Sanitization Policy"
        in aliases_by_name["Media Handling and Sanitization Policy"]
    )
    assert (
        "Application Partitioning Procedures"
        in aliases_by_name["Application Segmentation and Isolation Procedures"]
    )
    assert "Audit Logging Tools" in aliases_by_name["Audit Logging Tool Inventory"]


def test_sprint_3_10_batch_2_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "Auditable Events Procedures" in aliases_by_name["Audit Logging Procedures"]
    assert (
        "Network Boundary Protection Procedures"
        in aliases_by_name["Boundary Protection Procedures"]
    )


def test_sprint_3_10_batch_3_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "ISCM Strategy" in aliases_by_name["Continuous Monitoring Strategy"]
    assert (
        "FIPS Module Certificates"
        in aliases_by_name["Cryptographic Module Validation Certificates"]
    )
    assert "Designated Controlled Areas" in aliases_by_name["Controlled Area Register"]
    assert "SoD Procedures" in aliases_by_name["Separation of Duties Procedures"]
    assert "Login Banner Policy" in aliases_by_name["System Use Banner Policy"]
    assert "Facility Diagram or Layout" in aliases_by_name["Facility Diagram"]


def test_sprint_3_10_batch_4_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert (
        "Flaw Remediation Procedures"
        in aliases_by_name["Vulnerability Remediation Procedures"]
    )
    assert "IAM Policy" in aliases_by_name["Identity and Access Management Policy"]
    assert (
        "IAM Procedures" in aliases_by_name["Identity and Access Management Procedures"]
    )
    assert (
        "Incident Response Test Plan"
        in aliases_by_name["Incident Response Exercise Plan"]
    )
    assert (
        "Incident Response Training Curriculum"
        in aliases_by_name["Incident Response Training Materials"]
    )


def test_sprint_3_10_batch_5_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert (
        "Information Flow Control Policies"
        in aliases_by_name["Security Architecture Policy"]
    )
    assert (
        "Information Flow Enforcement Procedures"
        in aliases_by_name["Security Architecture Procedures"]
    )
    assert "Insider Risk Policy" in aliases_by_name["Insider Threat Policy"]
    assert "Insider Risk Procedures" in aliases_by_name["Insider Threat Procedures"]
    assert "Asset Inventory Policy" in aliases_by_name["Asset Management Policy"]
    assert (
        "Asset Inventory Procedures" in aliases_by_name["Asset Management Procedures"]
    )


def test_sprint_3_10_batch_7_preserves_approved_aliases() -> None:
    aliases_by_name = {item.canonical_name: item.aliases for item in EVIDENCE_KNOWLEDGE}

    assert "Service Account Permissions" in aliases_by_name["Access Control List"]
    assert (
        "Physical and Environmental Protection Policy"
        in aliases_by_name["Physical Security Policy"]
    )
    assert (
        "Public Relations Procedures"
        in aliases_by_name["Public Communications Procedures"]
    )
    assert (
        "Malicious Code Protection Procedures"
        in aliases_by_name["Malware Protection Procedures"]
    )


def test_remediation_plan_is_not_a_poam_category() -> None:
    remediation_plan = EVIDENCE_KNOWLEDGE[6]

    assert remediation_plan.category == EvidenceCategory.PLAN
    assert "POA&M" in remediation_plan.aliases
    assert not hasattr(EvidenceCategory, "POAM")


def test_knowledge_accessor_returns_the_immutable_catalog() -> None:
    assert evidence_knowledge() is EVIDENCE_KNOWLEDGE
