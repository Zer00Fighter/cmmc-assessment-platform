from __future__ import annotations

import pytest

from src.assessment_knowledge.models import (
    AssessmentMethodKind,
    CompiledAssessmentKnowledge,
)
from src.evidence_requests.catalog_compiler import (
    AssessmentProcedureRow,
    CatalogCompiler,
    CatalogCompilerError,
)


def make_row(
    *,
    framework_id: str = "CMMC_L2",
    family: str = "AC",
    requirement_id: str = "AC.L2-3.1.1",
    requirement_title: str = "Authorized Access Control",
    requirement_text: str = (
        "Limit system access to authorized users, "
        "processes acting on behalf of authorized "
        "users, and devices."
    ),
    objective_id: str = "a",
    objective_text: str = (
        "Authorized users are identified."
    ),
    examine: str = (
        "[SELECT FROM: "
        "access control policy; "
        "system security plan]"
    ),
    interview: str = "system administrators",
    test: str = (
        "mechanisms implementing access controls"
    ),
    sprs_weight: int | None = 5,
) -> AssessmentProcedureRow:
    return AssessmentProcedureRow(
        framework_id=framework_id,
        family=family,
        requirement_id=requirement_id,
        requirement_title=requirement_title,
        requirement_text=requirement_text,
        objective_id=objective_id,
        objective_text=objective_text,
        examine=examine,
        interview=interview,
        test=test,
        sprs_weight=sprs_weight,
        source_document="CMMC Assessment Guide",
        source_revision="2.13",
        source_location=(
            f"{requirement_id}[{objective_id}]"
            if objective_id
            else requirement_id
        ),
    )


def test_compile_returns_knowledge() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert isinstance(
        knowledge,
        CompiledAssessmentKnowledge,
    )


def test_compile_requirement() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert len(knowledge.requirements) == 1

    requirement = knowledge.requirements[0]

    assert requirement.framework_id == "CMMC_L2"
    assert (
        requirement.requirement_id
        == "AC.L2-3.1.1"
    )
    assert requirement.family == "AC"
    assert (
        requirement.title
        == "Authorized Access Control"
    )
    assert requirement.sprs_weight == 5


def test_compile_objective() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert len(knowledge.objectives) == 1

    objective = knowledge.objectives[0]

    assert objective.objective_id == "a"
    assert (
        objective.requirement_id
        == "AC.L2-3.1.1"
    )


def test_examine_compiles_to_evidence() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert len(knowledge.evidence) == 2

    ids = {
        item.canonical_id
        for item in knowledge.evidence
    }

    assert (
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
        in ids
    )

    assert (
        "EVIDENCE_SYSTEM_SECURITY_PLAN"
        in ids
    )


def test_interview_compiles_to_interview() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert len(knowledge.interviews) == 1

    interview = knowledge.interviews[0]

    assert (
        interview.title
        == "System Administrators"
    )


def test_test_compiles_to_test_target() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    assert len(knowledge.tests) == 1

    test = knowledge.tests[0]

    assert (
        test.title
        == "Mechanisms Implementing Access Controls"
    )


def test_requirement_links_to_compiled_objects() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    requirement = knowledge.requirements[0]

    assert (
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
        in requirement.evidence_ids
    )

    assert (
        "EVIDENCE_SYSTEM_SECURITY_PLAN"
        in requirement.evidence_ids
    )

    assert len(requirement.interview_ids) == 1
    assert len(requirement.test_ids) == 1


def test_objective_links_to_compiled_objects() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    objective = knowledge.objectives[0]

    assert (
        "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
        in objective.evidence_ids
    )

    assert (
        "EVIDENCE_SYSTEM_SECURITY_PLAN"
        in objective.evidence_ids
    )

    assert len(objective.interview_ids) == 1
    assert len(objective.test_ids) == 1


def test_requirement_level_row_without_objective() -> None:
    row = make_row(
        objective_id="",
        objective_text="",
    )

    knowledge = CatalogCompiler().compile(
        [row]
    )

    assert len(knowledge.requirements) == 1
    assert len(knowledge.objectives) == 0
    assert len(knowledge.evidence) == 2


def test_multiple_objectives_merge_into_requirement() -> None:
    rows = [
        make_row(
            objective_id="a",
            objective_text=(
                "Authorized users are identified."
            ),
        ),
        make_row(
            objective_id="b",
            objective_text=(
                "Authorized processes are identified."
            ),
            examine="system security plan",
            interview="system administrators",
            test="access authorization mechanisms",
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert len(knowledge.requirements) == 1
    assert len(knowledge.objectives) == 2

    requirement = knowledge.requirements[0]

    assert requirement.objective_ids == (
        "a",
        "b",
    )


def test_reused_evidence_is_merged_across_objectives() -> None:
    rows = [
        make_row(
            objective_id="a",
            examine="system security plan",
        ),
        make_row(
            objective_id="b",
            objective_text=(
                "Authorized processes are identified."
            ),
            examine="system security plan",
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert len(knowledge.evidence) == 1

    evidence = knowledge.evidence[0]

    assert (
        evidence.canonical_id
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )

    assert evidence.objective_ids == (
        "a",
        "b",
    )


def test_reused_evidence_is_merged_across_requirements() -> None:
    rows = [
        make_row(
            requirement_id="AC.L2-3.1.1",
            requirement_title=(
                "Authorized Access Control"
            ),
            objective_id="a",
            examine="system security plan",
        ),
        make_row(
            requirement_id="AC.L2-3.1.2",
            requirement_title=(
                "Transaction & Function Control"
            ),
            requirement_text=(
                "Limit system access to the types "
                "of transactions and functions "
                "authorized users may execute."
            ),
            objective_id="a",
            objective_text=(
                "Permitted transactions and "
                "functions are defined."
            ),
            examine="system security plan",
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert len(knowledge.evidence) == 1

    evidence = knowledge.evidence[0]

    assert evidence.requirement_ids == (
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    )

    assert evidence.reused is True


def test_provenance_is_preserved() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    evidence = next(
        item
        for item in knowledge.evidence
        if item.canonical_id
        == "EVIDENCE_SYSTEM_SECURITY_PLAN"
    )

    assert len(evidence.sources) == 1

    source = evidence.sources[0]

    assert (
        source.source_document
        == "CMMC Assessment Guide"
    )

    assert source.source_revision == "2.13"

    assert (
        source.method
        == AssessmentMethodKind.EXAMINE
    )


def test_interview_provenance_uses_interview_method() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    source = (
        knowledge.interviews[0]
        .sources[0]
    )

    assert (
        source.method
        == AssessmentMethodKind.INTERVIEW
    )


def test_test_provenance_uses_test_method() -> None:
    knowledge = CatalogCompiler().compile(
        [make_row()]
    )

    source = knowledge.tests[0].sources[0]

    assert (
        source.method
        == AssessmentMethodKind.TEST
    )


def test_mapping_input_supported() -> None:
    row = {
        "framework_id": "CMMC_L2",
        "family": "AC",
        "requirement_id": "AC.L2-3.1.1",
        "requirement_title": (
            "Authorized Access Control"
        ),
        "requirement_text": (
            "Limit system access to authorized users."
        ),
        "objective_id": "a",
        "objective_text": (
            "Authorized users are identified."
        ),
        "examine": "access control policy",
        "interview": "system administrators",
        "test": "access control mechanisms",
        "sprs_weight": 5,
    }

    knowledge = CatalogCompiler().compile(
        [row]
    )

    assert len(knowledge.requirements) == 1
    assert len(knowledge.evidence) == 1


def test_invalid_row_type_rejected() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        CatalogCompiler().compile(
            [123]
        )


def test_blank_framework_rejected() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        make_row(
            framework_id=""
        )


def test_blank_requirement_id_rejected() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        make_row(
            requirement_id=""
        )


def test_blank_requirement_text_rejected() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        make_row(
            requirement_text=""
        )


def test_objective_requires_text() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        make_row(
            objective_id="a",
            objective_text="",
        )


def test_negative_sprs_weight_rejected() -> None:
    with pytest.raises(
        CatalogCompilerError
    ):
        make_row(
            sprs_weight=-1
        )


def test_conflicting_requirement_text_rejected() -> None:
    rows = [
        make_row(
            objective_id="a",
        ),
        make_row(
            objective_id="b",
            objective_text="Objective B.",
            requirement_text=(
                "Different requirement text."
            ),
        ),
    ]

    with pytest.raises(
        CatalogCompilerError
    ):
        CatalogCompiler().compile(
            rows
        )


def test_conflicting_title_rejected() -> None:
    rows = [
        make_row(
            objective_id="a",
        ),
        make_row(
            objective_id="b",
            objective_text="Objective B.",
            requirement_title="Different Title",
        ),
    ]

    with pytest.raises(
        CatalogCompilerError
    ):
        CatalogCompiler().compile(
            rows
        )


def test_conflicting_family_rejected() -> None:
    rows = [
        make_row(),
        make_row(
            family="AU",
            objective_id="b",
            objective_text="Objective B.",
        ),
    ]

    with pytest.raises(
        CatalogCompilerError
    ):
        CatalogCompiler().compile(
            rows
        )


def test_conflicting_sprs_weight_rejected() -> None:
    rows = [
        make_row(
            sprs_weight=5,
        ),
        make_row(
            objective_id="b",
            objective_text="Objective B.",
            sprs_weight=3,
        ),
    ]

    with pytest.raises(
        CatalogCompilerError
    ):
        CatalogCompiler().compile(
            rows
        )


def test_missing_sprs_can_be_filled_later() -> None:
    rows = [
        make_row(
            sprs_weight=None,
        ),
        make_row(
            objective_id="b",
            objective_text="Objective B.",
            sprs_weight=5,
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert (
        knowledge.requirements[0]
        .sprs_weight
        == 5
    )


def test_duplicate_identical_rows_do_not_duplicate_links() -> None:
    row = make_row()

    knowledge = CatalogCompiler().compile(
        [
            row,
            row,
        ]
    )

    assert len(knowledge.requirements) == 1
    assert len(knowledge.objectives) == 1
    assert len(knowledge.evidence) == 2
    assert len(knowledge.interviews) == 1
    assert len(knowledge.tests) == 1


def test_empty_input_returns_empty_knowledge() -> None:
    knowledge = CatalogCompiler().compile(
        []
    )

    assert knowledge.requirements == ()
    assert knowledge.objectives == ()
    assert knowledge.evidence == ()
    assert knowledge.interviews == ()
    assert knowledge.tests == ()


def test_deterministic_requirement_order() -> None:
    rows = [
        make_row(
            requirement_id="AC.L2-3.1.2",
            requirement_title="Second",
            requirement_text="Second requirement.",
            objective_id="a",
            objective_text="Objective.",
        ),
        make_row(
            requirement_id="AC.L2-3.1.1",
            requirement_title="First",
            requirement_text="First requirement.",
            objective_id="a",
            objective_text="Objective.",
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert [
        item.requirement_id
        for item in knowledge.requirements
    ] == [
        "AC.L2-3.1.1",
        "AC.L2-3.1.2",
    ]


def test_multi_framework_compilation() -> None:
    rows = [
        make_row(),
        make_row(
            framework_id="PCI_DSS_4_0",
            family="8",
            requirement_id="8.3.1",
            requirement_title="Authentication",
            requirement_text=(
                "Authentication controls are implemented."
            ),
            objective_id="a",
            objective_text=(
                "Authentication controls are verified."
            ),
            examine="access control policy",
            interview="system administrators",
            test="authentication mechanisms",
            sprs_weight=None,
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    assert knowledge.framework_ids == (
        "CMMC_L2",
        "PCI_DSS_4_0",
    )

    assert len(knowledge.requirements) == 2


def test_cross_framework_evidence_reuse() -> None:
    rows = [
        make_row(
            examine="access control policy",
        ),
        make_row(
            framework_id="PCI_DSS_4_0",
            family="8",
            requirement_id="8.3.1",
            requirement_title="Authentication",
            requirement_text=(
                "Authentication controls are implemented."
            ),
            objective_id="a",
            objective_text=(
                "Authentication controls are verified."
            ),
            examine="access control policy",
            interview="",
            test="",
            sprs_weight=None,
        ),
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    evidence = next(
        item
        for item in knowledge.evidence
        if item.canonical_id
        == "EVIDENCE_POLICY_ACCESS_CONTROL_POLICY"
    )

    assert evidence.framework_ids == (
        "CMMC_L2",
        "PCI_DSS_4_0",
    )

    assert evidence.framework_count == 2


def test_statistics_reflect_compiled_graph() -> None:
    rows = [
        make_row(
            examine=(
                "access control policy; "
                "system security plan"
            )
        )
    ]

    knowledge = CatalogCompiler().compile(
        rows
    )

    stats = knowledge.statistics

    assert stats.requirement_count == 1
    assert stats.objective_count == 1
    assert stats.evidence_count == 2
    assert stats.interview_count == 1
    assert stats.test_count == 1