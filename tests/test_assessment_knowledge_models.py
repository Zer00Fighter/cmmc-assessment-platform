from __future__ import annotations

import pytest

from src.assessment_knowledge.models import (
    AssessmentKnowledgeModelError,
    AssessmentMethodKind,
    CompiledAssessmentKnowledge,
    CompiledEvidence,
    CompiledInterview,
    CompiledObjective,
    CompiledRequirement,
    CompiledTest,
    SourceReference,
    stable_guid,
)


def make_source(
    *,
    framework_id: str = "CMMC_L2",
    requirement_id: str = "AC.L2-3.1.1",
    objective_id: str = "a",
    method: AssessmentMethodKind | None = (
        AssessmentMethodKind.EXAMINE
    ),
) -> SourceReference:
    return SourceReference(
        framework_id=framework_id,
        family="AC",
        requirement_id=requirement_id,
        objective_id=objective_id,
        method=method,
        source_document="CMMC Assessment Guide",
        source_revision="2.13",
        source_location="AC.L2-3.1.1[a]",
    )


def make_requirement(
    *,
    framework_id: str = "CMMC_L2",
    requirement_id: str = "AC.L2-3.1.1",
    objective_ids=(
        "a",
        "b",
    ),
    evidence_ids=(
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY",
        "EVIDENCE_SYSTEM_SECURITY_PLAN",
    ),
) -> CompiledRequirement:
    return CompiledRequirement(
        framework_id=framework_id,
        requirement_id=requirement_id,
        family="AC",
        title="Authorized Access Control",
        requirement_text=(
            "Limit system access to authorized users, "
            "processes acting on behalf of authorized "
            "users, and devices."
        ),
        sprs_weight=5,
        objective_ids=objective_ids,
        evidence_ids=evidence_ids,
        interview_ids=(
            "EVIDENCE_INTERVIEW_SYSTEM_ADMINISTRATORS",
        ),
        test_ids=(
            "EVIDENCE_TEST_ACCESS_CONTROL_MECHANISMS",
        ),
        sources=(
            make_source(
                framework_id=framework_id,
                requirement_id=requirement_id,
                objective_id="",
                method=None,
            ),
        ),
    )


def make_objective(
    objective_id: str = "a",
) -> CompiledObjective:
    return CompiledObjective(
        framework_id="CMMC_L2",
        requirement_id="AC.L2-3.1.1",
        objective_id=objective_id,
        objective_text=(
            "Authorized users are identified."
        ),
        evidence_ids=(
            "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY",
        ),
        interview_ids=(
            "EVIDENCE_INTERVIEW_SYSTEM_ADMINISTRATORS",
        ),
        test_ids=(
            "EVIDENCE_TEST_ACCESS_CONTROL_MECHANISMS",
        ),
        sources=(
            make_source(
                objective_id=objective_id
            ),
        ),
    )


def make_evidence(
    *,
    canonical_id: str = (
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
    ),
    requirement_ids=(
        "AC.L2-3.1.1",
    ),
) -> CompiledEvidence:
    return CompiledEvidence(
        canonical_id=canonical_id,
        title="Access Control Policy",
        object_type="Policy",
        framework_ids=(
            "CMMC_L2",
        ),
        requirement_ids=requirement_ids,
        objective_ids=(
            "a",
        ),
        source_methods=(
            AssessmentMethodKind.EXAMINE,
        ),
        raw_descriptions=(
            "access control policy",
        ),
        sources=(
            make_source(),
        ),
    )


def make_interview() -> CompiledInterview:
    return CompiledInterview(
        canonical_id=(
            "EVIDENCE_INTERVIEW_SYSTEM_ADMINISTRATORS"
        ),
        title="System Administrators",
        framework_ids=(
            "CMMC_L2",
        ),
        requirement_ids=(
            "AC.L2-3.1.1",
        ),
        objective_ids=(
            "a",
        ),
        raw_descriptions=(
            "system administrators",
        ),
        sources=(
            make_source(
                method=AssessmentMethodKind.INTERVIEW
            ),
        ),
    )


def make_test() -> CompiledTest:
    return CompiledTest(
        canonical_id=(
            "EVIDENCE_TEST_ACCESS_CONTROL_MECHANISMS"
        ),
        title="Access Control Mechanisms",
        framework_ids=(
            "CMMC_L2",
        ),
        requirement_ids=(
            "AC.L2-3.1.1",
        ),
        objective_ids=(
            "a",
        ),
        raw_descriptions=(
            "mechanisms implementing access controls",
        ),
        sources=(
            make_source(
                method=AssessmentMethodKind.TEST
            ),
        ),
    )


def test_stable_guid_is_deterministic() -> None:
    first = stable_guid(
        "requirement",
        "CMMC_L2",
        "AC.L2-3.1.1",
    )

    second = stable_guid(
        "requirement",
        "CMMC_L2",
        "AC.L2-3.1.1",
    )

    assert first == second


def test_stable_guid_is_case_insensitive() -> None:
    first = stable_guid(
        "requirement",
        "CMMC_L2",
        "AC.L2-3.1.1",
    )

    second = stable_guid(
        "REQUIREMENT",
        "cmmc_l2",
        "ac.l2-3.1.1",
    )

    assert first == second


def test_stable_guid_has_uuid_like_format() -> None:
    guid = stable_guid(
        "evidence",
        "EVIDENCE_SYSTEM_SECURITY_PLAN",
    )

    parts = guid.split("-")

    assert [
        len(part)
        for part in parts
    ] == [
        8,
        4,
        4,
        4,
        12,
    ]


def test_source_reference_requires_framework() -> None:
    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        SourceReference(
            framework_id="",
        )


def test_source_reference_trims_values() -> None:
    source = SourceReference(
        framework_id=" CMMC_L2 ",
        family=" AC ",
        requirement_id=" AC.L2-3.1.1 ",
        objective_id=" a ",
    )

    assert source.framework_id == "CMMC_L2"
    assert source.family == "AC"
    assert (
        source.requirement_id
        == "AC.L2-3.1.1"
    )
    assert source.objective_id == "a"


def test_source_reference_key_is_case_insensitive() -> None:
    first = make_source()

    second = SourceReference(
        framework_id="cmmc_l2",
        family="ac",
        requirement_id="ac.l2-3.1.1",
        objective_id="A",
        method=AssessmentMethodKind.EXAMINE,
        source_document="cmmc assessment guide",
        source_revision="2.13",
        source_location="ac.l2-3.1.1[a]",
    )

    assert first.key == second.key


def test_compiled_requirement_generates_guid() -> None:
    requirement = make_requirement()

    assert requirement.guid
    assert (
        requirement.guid
        == stable_guid(
            "requirement",
            "CMMC_L2",
            "AC.L2-3.1.1",
        )
    )


def test_compiled_requirement_deduplicates_ids() -> None:
    requirement = make_requirement(
        objective_ids=(
            "a",
            "A",
            "b",
            "",
        ),
        evidence_ids=(
            "EV-1",
            "ev-1",
            "EV-2",
        ),
    )

    assert requirement.objective_ids == (
        "a",
        "b",
    )

    assert requirement.evidence_ids == (
        "EV-1",
        "EV-2",
    )


def test_compiled_requirement_negative_sprs_rejected() -> None:
    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        CompiledRequirement(
            framework_id="CMMC_L2",
            requirement_id="AC.L2-3.1.1",
            family="AC",
            title="Access Control",
            requirement_text="Requirement text.",
            sprs_weight=-1,
        )


def test_compiled_requirement_requires_text() -> None:
    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        CompiledRequirement(
            framework_id="CMMC_L2",
            requirement_id="AC.L2-3.1.1",
            family="AC",
            title="Access Control",
            requirement_text="",
        )


def test_compiled_objective_generates_guid() -> None:
    objective = make_objective()

    assert (
        objective.guid
        == stable_guid(
            "objective",
            "CMMC_L2",
            "AC.L2-3.1.1",
            "a",
        )
    )


def test_compiled_objective_requires_text() -> None:
    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        CompiledObjective(
            framework_id="CMMC_L2",
            requirement_id="AC.L2-3.1.1",
            objective_id="a",
            objective_text="",
        )


def test_compiled_evidence_generates_guid() -> None:
    evidence = make_evidence()

    assert (
        evidence.guid
        == stable_guid(
            "evidence",
            evidence.canonical_id,
        )
    )


def test_compiled_evidence_reuse_false_for_one_requirement() -> None:
    evidence = make_evidence()

    assert evidence.reused is False
    assert evidence.requirement_count == 1


def test_compiled_evidence_reuse_true_for_multiple_requirements() -> None:
    evidence = make_evidence(
        requirement_ids=(
            "AC.L2-3.1.1",
            "AC.L2-3.1.2",
            "AC.L2-3.1.5",
        )
    )

    assert evidence.reused is True
    assert evidence.requirement_count == 3


def test_compiled_evidence_supports_multiple_frameworks() -> None:
    evidence = CompiledEvidence(
        canonical_id="EVIDENCE_SYSTEM_SECURITY_PLAN",
        title="System Security Plan",
        object_type="System Security Plan",
        framework_ids=(
            "CMMC_L2",
            "NIST_800_53_R5",
            "cmmc_l2",
        ),
    )

    assert evidence.framework_ids == (
        "CMMC_L2",
        "NIST_800_53_R5",
    )

    assert evidence.framework_count == 2


def test_compiled_evidence_deduplicates_methods() -> None:
    evidence = CompiledEvidence(
        canonical_id="EVIDENCE_TEST",
        title="Test Evidence",
        object_type="Other",
        source_methods=(
            AssessmentMethodKind.EXAMINE,
            AssessmentMethodKind.EXAMINE,
            AssessmentMethodKind.TEST,
        ),
    )

    assert evidence.source_methods == (
        AssessmentMethodKind.EXAMINE,
        AssessmentMethodKind.TEST,
    )


def test_compiled_evidence_deduplicates_sources() -> None:
    source = make_source()

    evidence = CompiledEvidence(
        canonical_id="EVIDENCE_TEST",
        title="Test Evidence",
        object_type="Other",
        sources=(
            source,
            source,
        ),
    )

    assert evidence.sources == (
        source,
    )


def test_compiled_interview_generates_guid() -> None:
    interview = make_interview()

    assert (
        interview.guid
        == stable_guid(
            "interview",
            interview.canonical_id,
        )
    )


def test_compiled_test_generates_guid() -> None:
    test = make_test()

    assert (
        test.guid
        == stable_guid(
            "test",
            test.canonical_id,
        )
    )


def test_empty_compiled_knowledge() -> None:
    knowledge = (
        CompiledAssessmentKnowledge()
    )

    assert knowledge.requirements == ()
    assert knowledge.objectives == ()
    assert knowledge.evidence == ()
    assert knowledge.interviews == ()
    assert knowledge.tests == ()


def test_compiled_knowledge_indexes() -> None:
    requirement = make_requirement()
    objective = make_objective()
    evidence = make_evidence()
    interview = make_interview()
    test = make_test()

    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            requirement,
        ),
        objectives=(
            objective,
        ),
        evidence=(
            evidence,
        ),
        interviews=(
            interview,
        ),
        tests=(
            test,
        ),
    )

    assert (
        knowledge.get_requirement(
            "CMMC_L2",
            "AC.L2-3.1.1",
        )
        == requirement
    )

    assert (
        knowledge.get_objective(
            "CMMC_L2",
            "AC.L2-3.1.1",
            "a",
        )
        == objective
    )

    assert (
        knowledge.get_evidence(
            evidence.canonical_id
        )
        == evidence
    )


def test_requirement_lookup_is_case_insensitive() -> None:
    requirement = make_requirement()

    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            requirement,
        )
    )

    result = knowledge.get_requirement(
        "cmmc_l2",
        "ac.l2-3.1.1",
    )

    assert result == requirement


def test_unknown_requirement_raises() -> None:
    knowledge = (
        CompiledAssessmentKnowledge()
    )

    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        knowledge.get_requirement(
            "CMMC_L2",
            "DOES.NOT.EXIST",
        )


def test_unknown_objective_raises() -> None:
    knowledge = (
        CompiledAssessmentKnowledge()
    )

    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        knowledge.get_objective(
            "CMMC_L2",
            "AC.L2-3.1.1",
            "z",
        )


def test_unknown_evidence_raises() -> None:
    knowledge = (
        CompiledAssessmentKnowledge()
    )

    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        knowledge.get_evidence(
            "DOES_NOT_EXIST"
        )


def test_duplicate_evidence_canonical_id_rejected() -> None:
    evidence = make_evidence()

    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        CompiledAssessmentKnowledge(
            evidence=(
                evidence,
                evidence,
            )
        )


def test_duplicate_requirement_guid_rejected() -> None:
    first = make_requirement()

    second = CompiledRequirement(
        framework_id="CMMC_L2",
        requirement_id="DIFFERENT",
        family="AC",
        title="Different",
        requirement_text="Different.",
        guid=first.guid,
    )

    with pytest.raises(
        AssessmentKnowledgeModelError
    ):
        CompiledAssessmentKnowledge(
            requirements=(
                first,
                second,
            )
        )


def test_framework_ids() -> None:
    cmmc = make_requirement()

    pci = CompiledRequirement(
        framework_id="PCI_DSS_4_0",
        requirement_id="8.3.1",
        family="8",
        title="Authentication",
        requirement_text=(
            "Authentication controls are implemented."
        ),
    )

    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            pci,
            cmmc,
        )
    )

    assert knowledge.framework_ids == (
        "CMMC_L2",
        "PCI_DSS_4_0",
    )


def test_statistics_empty_knowledge() -> None:
    stats = (
        CompiledAssessmentKnowledge()
        .statistics
    )

    assert stats.requirement_count == 0
    assert stats.objective_count == 0
    assert stats.evidence_count == 0
    assert stats.reusable_evidence_count == 0
    assert stats.interview_count == 0
    assert stats.test_count == 0

    assert (
        stats.average_evidence_per_requirement
        == 0.0
    )

    assert (
        stats.average_objectives_per_requirement
        == 0.0
    )


def test_statistics() -> None:
    requirement_one = make_requirement()

    requirement_two = CompiledRequirement(
        framework_id="CMMC_L2",
        requirement_id="AC.L2-3.1.2",
        family="AC",
        title="Transaction Control",
        requirement_text=(
            "Limit system access to authorized "
            "transactions and functions."
        ),
        objective_ids=(
            "a",
        ),
        evidence_ids=(
            "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY",
        ),
    )

    evidence = make_evidence(
        requirement_ids=(
            "AC.L2-3.1.1",
            "AC.L2-3.1.2",
        )
    )

    knowledge = CompiledAssessmentKnowledge(
        requirements=(
            requirement_one,
            requirement_two,
        ),
        objectives=(
            make_objective("a"),
            make_objective("b"),
        ),
        evidence=(
            evidence,
        ),
        interviews=(
            make_interview(),
        ),
        tests=(
            make_test(),
        ),
    )

    stats = knowledge.statistics

    assert stats.requirement_count == 2
    assert stats.objective_count == 2
    assert stats.evidence_count == 1
    assert stats.reusable_evidence_count == 1
    assert stats.interview_count == 1
    assert stats.test_count == 1

    # Requirement 1 has two evidence IDs;
    # Requirement 2 has one.
    assert (
        stats.average_evidence_per_requirement
        == 1.5
    )

    # Requirement 1 has two objectives;
    # Requirement 2 has one.
    assert (
        stats.average_objectives_per_requirement
        == 1.5
    )


def test_custom_guid_is_preserved() -> None:
    requirement = CompiledRequirement(
        framework_id="TEST",
        requirement_id="CTRL-1",
        family="TEST",
        title="Test",
        requirement_text="Test requirement.",
        guid="custom-guid",
    )

    assert requirement.guid == "custom-guid"


def test_models_are_immutable() -> None:
    requirement = make_requirement()

    with pytest.raises(
        (AttributeError, TypeError)
    ):
        requirement.title = "Changed"