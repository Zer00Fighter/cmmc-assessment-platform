from __future__ import annotations

import pytest

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject
from src.evidence.evidence_resolver import (
    EvidenceResolutionStatus,
    EvidenceResolver,
    EvidenceResolverError,
)


def test_knowledge_contains_approved_first_one_hundred_forty_nine_objects() -> None:
    assert len(EVIDENCE_KNOWLEDGE) == 149
    assert EVIDENCE_KNOWLEDGE[0].evidence_id == "EV-0001"
    assert EVIDENCE_KNOWLEDGE[-1].evidence_id == "EV-0149"


def test_resolves_canonical_name_exactly() -> None:
    result = EvidenceResolver().resolve("Credential Policy")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0016"
    assert result.evidence.canonical_name == "Credential Policy"


def test_resolves_alias_exactly() -> None:
    result = EvidenceResolver().resolve("Password Policy")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0016"
    assert result.matched_name == "Password Policy"


def test_resolution_is_case_insensitive_and_trimmed() -> None:
    result = EvidenceResolver().resolve("  system security plan  ")

    assert result.status == EvidenceResolutionStatus.EXACT
    assert result.evidence_id == "EV-0001"


def test_punctuation_variation_is_not_resolved() -> None:
    result = EvidenceResolver().resolve("Access-Control Policy & Procedures")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert result.evidence_id is None


def test_unknown_name_is_unresolved() -> None:
    result = EvidenceResolver().resolve("Quantum Security Ledger")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert not result.resolved
    assert result.evidence is None
    assert result.evidence_id is None


def test_blank_name_is_unresolved() -> None:
    result = EvidenceResolver().resolve("   ")

    assert result.status == EvidenceResolutionStatus.UNRESOLVED
    assert result.source_name == ""


def test_resolve_many_preserves_input_order() -> None:
    results = EvidenceResolver().resolve_many(("POA&M", "Unknown", "User Account List"))

    assert [result.evidence_id for result in results] == [
        "EV-0007",
        None,
        "EV-0011",
    ]


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("List of System Accounts", "EV-0011"),
        ("Privileged Account List", "EV-0012"),
        ("Access Approval Records", "EV-0013"),
        ("Access Recertification Records", "EV-0014"),
        ("Password Policy", "EV-0016"),
        ("MFA Configuration", "EV-0018"),
        ("VPN Configuration", "EV-0019"),
        ("IdP Configuration", "EV-0020"),
    ),
)
def test_cross_framework_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Device Inventory", "EV-0021"),
        ("Application Inventory", "EV-0022"),
        ("Data Inventory", "EV-0023"),
        ("Hardening Standard", "EV-0027"),
        ("Change Tickets", "EV-0029"),
        ("Network Topology Diagram", "EV-0031"),
        ("System Design Documentation", "EV-0033"),
        ("Firewall Rules", "EV-0035"),
        ("System Logs", "EV-0036"),
        ("SIEM Configuration", "EV-0039"),
        ("SIEM Alerts", "EV-0040"),
    ),
)
def test_sprint_3_5_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("IR Plan", "EV-0041"),
        ("Incident Tickets", "EV-0043"),
        ("Tabletop Exercise Results", "EV-0044"),
        ("BCP", "EV-0046"),
        ("DRP", "EV-0047"),
        ("Backup Logs", "EV-0049"),
        ("Badge Access Logs", "EV-0053"),
        ("Visitor Logs", "EV-0054"),
        ("Background Check Records", "EV-0056"),
        ("Offboarding Records", "EV-0059"),
        ("Security Awareness Training Records", "EV-0060"),
    ),
)
def test_sprint_3_6_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Vendor Inventory", "EV-0061"),
        ("Vendor Risk Assessment", "EV-0062"),
        ("Third-Party Security Questionnaire", "EV-0063"),
        ("Service Provider Agreements", "EV-0064"),
        ("Encryption Policy", "EV-0068"),
        ("Key Rotation Records", "EV-0072"),
        ("TLS Certificate Inventory", "EV-0074"),
        ("SOC Procedures", "EV-0075"),
        ("Vulnerability Scan Results", "EV-0076"),
        ("Patch Deployment Records", "EV-0078"),
        ("Endpoint Protection Configuration", "EV-0079"),
    ),
)
def test_sprint_3_7_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Logical Access Control Policy", "EV-0081"),
        ("ACL", "EV-0083"),
        ("Access Credentials", "EV-0085"),
        ("CM Plan", "EV-0087"),
        ("System Media Protection Policy", "EV-0091"),
        ("System Media", "EV-0093"),
        ("Equipment Sanitization Records", "EV-0094"),
        ("System Maintenance Policy", "EV-0096"),
        ("Maintenance Logs", "EV-0098"),
    ),
)
def test_sprint_3_9_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Mobile Device Security Procedures", "EV-0101"),
        ("Account Management Compliance Reviews", "EV-0102"),
        ("Configuration Control Board Minutes", "EV-0103"),
        ("Remote Work Site Security Procedures", "EV-0104"),
        ("Security Analysis Outputs", "EV-0106"),
        ("Media Sanitization Policy", "EV-0107"),
        ("Application Partitioning Procedures", "EV-0108"),
        ("Remote Work Site Security Assessment", "EV-0109"),
        ("Audit Logging Tools", "EV-0111"),
    ),
)
def test_sprint_3_10_batch_1_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Auditable Events Procedures", "EV-0112"),
        ("Network Boundary Protection Procedures", "EV-0113"),
    ),
)
def test_sprint_3_10_batch_2_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("ISCM Strategy", "EV-0117"),
        ("FIPS Module Certificates", "EV-0118"),
        ("Designated Controlled Areas", "EV-0120"),
        ("SoD Procedures", "EV-0122"),
        ("Login Banner Policy", "EV-0123"),
        ("Facility Diagram or Layout", "EV-0124"),
    ),
)
def test_sprint_3_10_batch_3_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Flaw Remediation Procedures", "EV-0125"),
        ("IAM Policy", "EV-0126"),
        ("IAM Procedures", "EV-0127"),
        ("Incident Response Test Plan", "EV-0129"),
        ("Incident Response Testing Material", "EV-0130"),
        ("Incident Response Testing Procedures", "EV-0131"),
        ("Incident Response Training Curriculum", "EV-0132"),
        ("IR Training Procedures", "EV-0133"),
    ),
)
def test_sprint_3_10_batch_4_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Information Flow Control Policies", "EV-0134"),
        ("Information Flow Enforcement Procedures", "EV-0135"),
        ("Insider Risk Policy", "EV-0136"),
        ("Insider Risk Procedures", "EV-0137"),
        ("Asset Inventory Policy", "EV-0138"),
        ("Asset Inventory Procedures", "EV-0139"),
    ),
)
def test_sprint_3_10_batch_5_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Service Account Permissions", "EV-0083"),
        ("Physical and Environmental Protection Policy", "EV-0140"),
        ("Public Relations Procedures", "EV-0141"),
        ("Malicious Code Protection Procedures", "EV-0142"),
    ),
)
def test_sprint_3_10_batch_7_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Risk Analysis Procedures", "EV-0143"),
        ("HR Manual", "EV-0144"),
        ("Employee Handbook", "EV-0144"),
    ),
)
def test_sprint_3_10_batch_8_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("ERM Policy", "EV-0145"),
        ("Rules of Behavior", "EV-0146"),
        ("AUP", "EV-0146"),
    ),
)
def test_sprint_3_10_batch_10_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


@pytest.mark.parametrize(
    ("alias", "evidence_id"),
    (
        ("Security Assessments Procedures", "EV-0147"),
        ("Security Training Policy", "EV-0148"),
        ("Security Awareness Training Curriculum", "EV-0149"),
        ("Security Awareness Training Materials", "EV-0149"),
    ),
)
def test_sprint_3_10_batch_11_aliases_resolve(alias: str, evidence_id: str) -> None:
    assert EvidenceResolver().resolve(alias).evidence_id == evidence_id


def test_ambiguous_names_are_rejected() -> None:
    first = EvidenceObject(
        evidence_id="EV-A",
        canonical_name="First Policy",
        aliases=("Shared Name",),
    )
    second = EvidenceObject(
        evidence_id="EV-B",
        canonical_name="Second Policy",
        aliases=("shared name",),
    )

    with pytest.raises(
        EvidenceResolverError,
        match="Ambiguous Evidence Object name",
    ):
        EvidenceResolver((first, second))
