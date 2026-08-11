from __future__ import annotations

from src.assessment_knowledge.models import (
    CompiledAssessmentKnowledge,
    CompiledEvidence,
)
from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestControl,
    DocumentationRequestPriority,
    DocumentationRequestType,
)
from src.evidence_requests.evidence_coverage_audit import (
    EvidenceCoverageAuditor,
    EvidenceCoverageMatchKind,
)


def request(
    request_id: str,
    title: str,
    *,
    family: str,
    evidence_type: DocumentationRequestType = DocumentationRequestType.OTHER,
) -> DocumentationRequest:
    return DocumentationRequest(
        request_id=request_id,
        requested_item=title,
        evidence_type=evidence_type,
        priority=DocumentationRequestPriority.LOW,
        controls=[
            DocumentationRequestControl(
                framework_id="TEST",
                control_id=f"{family}-1",
                family=family,
            )
        ],
    )


def test_audit_classifies_canonical_alias_and_unresolved_titles() -> None:
    collection = DocumentationRequestCollection(
        framework_id="TEST",
        requests=[
            request("DRL-001", "Security Plan", family="CA"),
            request("DRL-002", "SSP", family="CA"),
            request("DRL-003", "Unknown Artifact", family="AC"),
        ],
    )

    report = EvidenceCoverageAuditor().audit(collection)

    assert report.total_requests == 3
    assert report.canonical_matches == 1
    assert report.alias_matches == 1
    assert report.unresolved == 1
    assert report.coverage_percent == 66.67
    assert report.unresolved_titles == ("Unknown Artifact",)
    assert [entry.match_kind for entry in report.entries] == [
        EvidenceCoverageMatchKind.CANONICAL,
        EvidenceCoverageMatchKind.ALIAS,
        EvidenceCoverageMatchKind.UNRESOLVED,
    ]


def test_audit_preserves_control_and_objective_traceability() -> None:
    collection = DocumentationRequestCollection(
        framework_id="TEST",
        requests=[request("DRL-001", "Password Policy", family="IA")],
    )
    knowledge = CompiledAssessmentKnowledge(
        evidence=(
            CompiledEvidence(
                canonical_id="SOURCE-001",
                title="Password Policy",
                object_type="Examine",
                framework_ids=("TEST",),
                requirement_ids=("IA-1",),
                objective_ids=("a", "b"),
            ),
        )
    )

    entry = (
        EvidenceCoverageAuditor()
        .audit(
            collection,
            knowledge=knowledge,
        )
        .entries[0]
    )

    assert entry.evidence_id == "EV-0016"
    assert entry.canonical_name == "Credential Policy"
    assert entry.control_ids == ("IA-1",)
    assert entry.objective_ids == ("a", "b")


def test_audit_reports_coverage_by_family_and_evidence_type() -> None:
    collection = DocumentationRequestCollection(
        framework_id="TEST",
        requests=[
            request(
                "DRL-001",
                "Security Plan",
                family="CA",
                evidence_type=DocumentationRequestType.PLAN,
            ),
            request(
                "DRL-002",
                "Unknown Artifact",
                family="CA",
                evidence_type=DocumentationRequestType.OTHER,
            ),
        ],
    )

    report = EvidenceCoverageAuditor().audit(collection)

    assert report.by_control_family[0].name == "CA"
    assert report.by_control_family[0].coverage_percent == 50.0
    assert {
        group.name: group.coverage_percent for group in report.by_evidence_type
    } == {
        "Other": 0.0,
        "Plan": 100.0,
    }


def test_empty_collection_has_zero_coverage() -> None:
    report = EvidenceCoverageAuditor().audit(
        DocumentationRequestCollection(framework_id="TEST")
    )

    assert report.total_requests == 0
    assert report.coverage_percent == 0.0
    assert report.objective_trace_percent == 0.0
    assert report.by_control_family == ()


def test_audit_reports_missing_objective_traceability() -> None:
    collection = DocumentationRequestCollection(
        framework_id="TEST",
        requests=[request("DRL-001", "Security Plan", family="CA")],
    )

    report = EvidenceCoverageAuditor().audit(collection)

    assert report.objective_traced_requests == 0
    assert report.missing_objective_trace == 1
    assert report.missing_objective_titles == ("Security Plan",)


def test_audit_supports_curated_one_to_many_source_mapping() -> None:
    collection = DocumentationRequestCollection(
        framework_id="TEST",
        requests=[
            request(
                "DRL-001",
                "Security Plan System Design Documentation",
                family="CA",
            )
        ],
    )

    report = EvidenceCoverageAuditor().audit(collection)
    entry = report.entries[0]

    assert entry.match_kind == EvidenceCoverageMatchKind.CURATED_MAPPING
    assert entry.evidence_ids == ("EV-0001", "EV-0033")
    assert entry.canonical_names == (
        "Security Plan",
        "System Architecture Documentation",
    )
    assert entry.evidence_id is None
    assert report.curated_mappings == 1
