from __future__ import annotations

from src.assessment_knowledge.models import (
    AssessmentMethodKind,
    CompiledAssessmentKnowledge,
    CompiledEvidence,
    CompiledRequirement,
    SourceReference,
)
from src.evidence_requests.drl_model import (
    DocumentationRequestPriority,
    DocumentationRequestStatus,
    DocumentationRequestType,
)
from src.evidence_requests.request_generator import (
    RequestGenerator,
    RequestGeneratorOptions,
)


def make_requirement(
    requirement_id: str,
    *,
    family: str = "AC",
    title: str = "Requirement",
) -> CompiledRequirement:
    return CompiledRequirement(
        framework_id="CMMC_L2",
        requirement_id=requirement_id,
        family=family,
        title=title,
        requirement_text="Requirement text.",
    )


def make_source(
    requirement_id: str,
    *,
    family: str = "AC",
) -> SourceReference:
    return SourceReference(
        framework_id="CMMC_L2",
        family=family,
        requirement_id=requirement_id,
        method=AssessmentMethodKind.EXAMINE,
        source_document="NIST SP 800-171A",
    )


def make_evidence(
    canonical_id: str,
    title: str,
    requirement_ids: tuple[str, ...],
    *,
    object_type: str = "Document",
    raw_descriptions: tuple[str, ...] = (),
) -> CompiledEvidence:
    return CompiledEvidence(
        canonical_id=canonical_id,
        title=title,
        object_type=object_type,
        framework_ids=("CMMC_L2",),
        requirement_ids=requirement_ids,
        source_methods=(AssessmentMethodKind.EXAMINE,),
        raw_descriptions=raw_descriptions,
        sources=tuple(
            make_source(requirement_id)
            for requirement_id in requirement_ids
        ),
    )


def test_generate_returns_collection() -> None:
    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            make_requirement("AC.L2-3.1.1"),
        ),
        evidence=(
            make_evidence(
                "EVIDENCE_POLICY_ACCESS_CONTROL",
                "Access Control Policy",
                ("AC.L2-3.1.1",),
            ),
        ),
    )

    result = RequestGenerator().generate(
        knowledge,
        framework_id="CMMC_L2",
        engagement_name="Assessment 2026",
        organization_name="Example Company",
    )

    assert result.framework_id == "CMMC_L2"
    assert result.engagement_name == "Assessment 2026"
    assert result.organization_name == "Example Company"
    assert result.count == 1


def test_generate_uses_canonical_control_ids() -> None:
    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            make_requirement(
                "AC.L2-3.1.1",
                title="Authorized Access Control",
            ),
        ),
        evidence=(
            make_evidence(
                "EVIDENCE_POLICY_ACCESS_CONTROL",
                "Access Control Policy",
                ("AC.L2-3.1.1",),
            ),
        ),
    )

    result = RequestGenerator().generate(
        knowledge,
        framework_id="CMMC_L2",
    )

    request = result.requests[0]

    assert request.control_ids == (
        "AC.L2-3.1.1",
    )

    assert (
        request.controls[0].control_title
        == "Authorized Access Control"
    )


def test_reused_evidence_becomes_one_request() -> None:
    requirements = (
        make_requirement("AC.L2-3.1.1"),
        make_requirement("AC.L2-3.1.2"),
        make_requirement("AC.L2-3.1.3"),
    )

    evidence = make_evidence(
        "EVIDENCE_POLICY_ACCESS_CONTROL",
        "Access Control Policy",
        tuple(
            item.requirement_id
            for item in requirements
        ),
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=requirements,
            evidence=(evidence,),
        ),
        framework_id="CMMC_L2",
    )

    assert result.count == 1
    request = result.requests[0]
    assert request.reuse_count == 3
    assert request.control_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
        "AC.L2-3.1.3",
    )


def test_priority_is_based_on_reuse() -> None:
    requirements = tuple(
        make_requirement(
            f"AC.L2-3.1.{number}"
        )
        for number in range(1, 7)
    )

    low = make_evidence(
        "EVIDENCE_LOW",
        "Low Evidence",
        (requirements[0].requirement_id,),
    )

    medium = make_evidence(
        "EVIDENCE_MEDIUM",
        "Medium Evidence",
        (
            requirements[0].requirement_id,
            requirements[1].requirement_id,
        ),
    )

    high = make_evidence(
        "EVIDENCE_HIGH",
        "High Evidence",
        tuple(
            item.requirement_id
            for item in requirements[:5]
        ),
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=requirements,
            evidence=(low, medium, high),
        ),
        framework_id="CMMC_L2",
    )

    by_item = {
        request.requested_item: request
        for request in result.requests
    }

    assert (
        by_item["Low Evidence"].priority
        == DocumentationRequestPriority.LOW
    )

    assert (
        by_item["Medium Evidence"].priority
        == DocumentationRequestPriority.MEDIUM
    )

    assert (
        by_item["High Evidence"].priority
        == DocumentationRequestPriority.HIGH
    )


def test_request_ids_are_deterministic() -> None:
    requirement = make_requirement(
        "AC.L2-3.1.1"
    )

    knowledge = CompiledAssessmentKnowledge(
        requirements=(requirement,),
        evidence=(
            make_evidence(
                "EVIDENCE_Z",
                "Z Evidence",
                (requirement.requirement_id,),
            ),
            make_evidence(
                "EVIDENCE_A",
                "A Evidence",
                (requirement.requirement_id,),
            ),
        ),
    )

    result = RequestGenerator().generate(
        knowledge,
        framework_id="CMMC_L2",
    )

    assert [
        request.request_id
        for request in result.requests
    ] == [
        "DRL-001",
        "DRL-002",
    ]

    assert [
        request.requested_item
        for request in result.requests
    ] == [
        "A Evidence",
        "Z Evidence",
    ]


def test_default_status_is_not_requested() -> None:
    requirement = make_requirement(
        "AC.L2-3.1.1"
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=(requirement,),
            evidence=(
                make_evidence(
                    "EVIDENCE_POLICY",
                    "Policy",
                    (requirement.requirement_id,),
                ),
            ),
        ),
        framework_id="CMMC_L2",
    )

    assert (
        result.requests[0].review_status
        == DocumentationRequestStatus.NOT_REQUESTED
    )

    assert result.requests[0].generated is True


def test_policy_type_is_inferred() -> None:
    requirement = make_requirement(
        "AC.L2-3.1.1"
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=(requirement,),
            evidence=(
                make_evidence(
                    "EVIDENCE_POLICY",
                    "Access Control Policy",
                    (requirement.requirement_id,),
                ),
            ),
        ),
        framework_id="CMMC_L2",
    )

    assert (
        result.requests[0].evidence_type
        == DocumentationRequestType.POLICY
    )


def test_system_security_plan_type_is_inferred() -> None:
    requirement = make_requirement(
        "CA.L2-3.12.4",
        family="CA",
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=(requirement,),
            evidence=(
                make_evidence(
                    "EVIDENCE_SYSTEM_SECURITY_PLAN",
                    "System Security Plan",
                    (requirement.requirement_id,),
                ),
            ),
        ),
        framework_id="CMMC_L2",
    )

    assert (
        result.requests[0].evidence_type
        == DocumentationRequestType.SYSTEM_SECURITY_PLAN
    )


def test_description_uses_raw_source_wording() -> None:
    requirement = make_requirement(
        "AC.L2-3.1.1"
    )

    result = RequestGenerator().generate(
        CompiledAssessmentKnowledge(
            requirements=(requirement,),
            evidence=(
                make_evidence(
                    "EVIDENCE_POLICY",
                    "Access Control Policy",
                    (requirement.requirement_id,),
                    raw_descriptions=(
                        "Access control policy.",
                        "Access control procedures.",
                    ),
                ),
            ),
        ),
        framework_id="CMMC_L2",
    )

    assert result.requests[0].description == (
        "Access control policy. | "
        "Access control procedures."
    )


def test_custom_priority_thresholds() -> None:
    requirements = tuple(
        make_requirement(
            f"AC.L2-3.1.{number}"
        )
        for number in range(1, 4)
    )

    evidence = make_evidence(
        "EVIDENCE_POLICY",
        "Access Control Policy",
        tuple(
            item.requirement_id
            for item in requirements
        ),
    )

    generator = RequestGenerator(
        RequestGeneratorOptions(
            high_priority_reuse_threshold=3,
            medium_priority_reuse_threshold=2,
        )
    )

    result = generator.generate(
        CompiledAssessmentKnowledge(
            requirements=requirements,
            evidence=(evidence,),
        ),
        framework_id="CMMC_L2",
    )

    assert (
        result.requests[0].priority
        == DocumentationRequestPriority.HIGH
    )