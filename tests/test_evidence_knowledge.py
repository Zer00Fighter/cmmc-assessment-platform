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
)


def test_knowledge_contains_the_approved_first_twenty_objects() -> None:
    assert tuple(item.evidence_id for item in EVIDENCE_KNOWLEDGE) == tuple(
        f"EV-{index:04d}" for index in range(1, 21)
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


def test_remediation_plan_is_not_a_poam_category() -> None:
    remediation_plan = EVIDENCE_KNOWLEDGE[6]

    assert remediation_plan.category == EvidenceCategory.PLAN
    assert "POA&M" in remediation_plan.aliases
    assert not hasattr(EvidenceCategory, "POAM")


def test_knowledge_accessor_returns_the_immutable_catalog() -> None:
    assert evidence_knowledge() is EVIDENCE_KNOWLEDGE
