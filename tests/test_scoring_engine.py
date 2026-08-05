from pathlib import Path

import pytest

from src.scoring import (
    AssessmentFinding,
    PartialImplementationState,
    RequirementAssessment,
    ScoringEngine,
    ScoringEngineError,
)


ROOT = Path(__file__).resolve().parents[1]

SCORING_WEIGHTS_PATH = (
    ROOT
    / "data"
    / "scoring"
    / "scoring_weights.csv"
)


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine(
        scoring_weights_csv=SCORING_WEIGHTS_PATH
    )


def build_all_met_assessments(
    engine: ScoringEngine,
) -> list[RequirementAssessment]:
    assessments: list[RequirementAssessment] = []

    for rule in engine.rules.values():
        assessments.append(
            RequirementAssessment(
                requirement_id=rule.requirement_id,
                finding=AssessmentFinding.MET,
                implementation_state=(
                    PartialImplementationState.FULLY_IMPLEMENTED
                    if rule.partial_credit_allowed
                    else None
                ),
            )
        )

    return assessments


def build_all_not_met_assessments(
    engine: ScoringEngine,
) -> list[RequirementAssessment]:
    assessments: list[RequirementAssessment] = []

    for rule in engine.rules.values():
        assessments.append(
            RequirementAssessment(
                requirement_id=rule.requirement_id,
                finding=AssessmentFinding.NOT_MET,
                implementation_state=(
                    PartialImplementationState.NOT_IMPLEMENTED
                    if rule.partial_credit_allowed
                    else None
                ),
            )
        )

    return assessments


def replace_assessment(
    assessments: list[RequirementAssessment],
    replacement: RequirementAssessment,
) -> list[RequirementAssessment]:
    return [
        replacement
        if assessment.requirement_id
        == replacement.requirement_id
        else assessment
        for assessment in assessments
    ]


def test_engine_loads_110_rules(
    engine: ScoringEngine,
) -> None:
    assert len(engine.rules) == 110


def test_engine_loads_expected_first_rule(
    engine: ScoringEngine,
) -> None:
    rule = engine.get_rule("AC.L2-3.1.1")

    assert rule.requirement_id == "AC.L2-3.1.1"
    assert rule.domain_code == "AC"
    assert rule.full_deduction_points in {1, 3, 5}


def test_default_assessments_are_not_assessed(
    engine: ScoringEngine,
) -> None:
    assessments = engine.create_default_assessments()

    assert len(assessments) == 110

    assert all(
        assessment.finding
        == AssessmentFinding.NOT_ASSESSED
        for assessment in assessments
    )


def test_default_assessment_result_is_incomplete(
    engine: ScoringEngine,
) -> None:
    result = engine.calculate(
        engine.create_default_assessments()
    )

    assert result.requirement_count == 110
    assert result.current_score == 110
    assert result.total_deduction_points == 0
    assert result.not_assessed_count == 110
    assert result.assessed_count == 0
    assert result.complete is False
    assert result.completion_percentage == 0.0


def test_all_met_produces_maximum_score(
    engine: ScoringEngine,
) -> None:
    result = engine.calculate(
        build_all_met_assessments(engine)
    )

    assert result.current_score == 110
    assert result.total_deduction_points == 0
    assert result.met_count == 110
    assert result.not_met_count == 0
    assert result.not_assessed_count == 0
    assert result.complete is True
    assert result.completion_percentage == 1.0


def test_all_not_met_produces_mathematical_minimum(
    engine: ScoringEngine,
) -> None:
    result = engine.calculate(
        build_all_not_met_assessments(engine)
    )

    assert result.maximum_score == 110
    assert result.maximum_possible_deduction == 314
    assert result.total_deduction_points == 314
    assert result.current_score == -204
    assert result.mathematical_minimum_score == -204
    assert result.not_met_count == 110
    assert result.complete is True


@pytest.mark.parametrize(
    ("requirement_id", "expected_deduction"),
    [
        ("AC.L2-3.1.1", 5),
        ("AU.L2-3.3.2", 3),
    ],
)
def test_fixed_weight_requirement_deductions(
    engine: ScoringEngine,
    requirement_id: str,
    expected_deduction: int,
) -> None:
    assessment = RequirementAssessment(
        requirement_id=requirement_id,
        finding=AssessmentFinding.NOT_MET,
    )

    result = engine.score_requirement(assessment)

    assert result.deduction_points == expected_deduction
    assert result.maximum_deduction_points == (
        expected_deduction
    )
    assert result.partial_credit_applied is False


def test_one_point_requirement_deduction(
    engine: ScoringEngine,
) -> None:
    one_point_rule = next(
        rule
        for rule in engine.rules.values()
        if rule.scoring_category == "ONE_POINT"
    )

    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id=one_point_rule.requirement_id,
            finding=AssessmentFinding.NOT_MET,
        )
    )

    assert result.deduction_points == 1
    assert result.maximum_deduction_points == 1


def test_partial_mfa_deducts_three_points(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="IA.L2-3.5.3",
            finding=AssessmentFinding.NOT_MET,
            implementation_state=(
                PartialImplementationState.PARTIALLY_IMPLEMENTED
            ),
        )
    )

    assert result.deduction_points == 3
    assert result.maximum_deduction_points == 5
    assert result.partial_credit_applied is True


def test_missing_mfa_deducts_five_points(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="IA.L2-3.5.3",
            finding=AssessmentFinding.NOT_MET,
            implementation_state=(
                PartialImplementationState.NOT_IMPLEMENTED
            ),
        )
    )

    assert result.deduction_points == 5
    assert result.partial_credit_applied is False


def test_non_fips_encryption_deducts_three_points(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="SC.L2-3.13.11",
            finding=AssessmentFinding.NOT_MET,
            implementation_state=(
                PartialImplementationState.PARTIALLY_IMPLEMENTED
            ),
        )
    )

    assert result.deduction_points == 3
    assert result.partial_credit_applied is True


def test_missing_encryption_deducts_five_points(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="SC.L2-3.13.11",
            finding=AssessmentFinding.NOT_MET,
            implementation_state=(
                PartialImplementationState.NOT_IMPLEMENTED
            ),
        )
    )

    assert result.deduction_points == 5
    assert result.partial_credit_applied is False


def test_not_applicable_has_zero_deduction(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="AC.L2-3.1.1",
            finding=AssessmentFinding.NOT_APPLICABLE,
            applicable=False,
        )
    )

    assert result.deduction_points == 0
    assert result.applicable is False
    assert result.assessed is True


def test_not_assessed_has_zero_current_deduction(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="AC.L2-3.1.1",
            finding=AssessmentFinding.NOT_ASSESSED,
        )
    )

    assert result.deduction_points == 0
    assert result.assessed is False


def test_single_five_point_failure_scores_105(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)

    assessments = replace_assessment(
        assessments,
        RequirementAssessment(
            requirement_id="AC.L2-3.1.1",
            finding=AssessmentFinding.NOT_MET,
        ),
    )

    result = engine.calculate(assessments)

    assert result.current_score == 105
    assert result.total_deduction_points == 5
    assert result.met_count == 109
    assert result.not_met_count == 1


def test_single_three_point_failure_scores_107(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)

    assessments = replace_assessment(
        assessments,
        RequirementAssessment(
            requirement_id="AU.L2-3.3.2",
            finding=AssessmentFinding.NOT_MET,
        ),
    )

    result = engine.calculate(assessments)

    assert result.current_score == 107
    assert result.total_deduction_points == 3


def test_partial_credit_assessment_scores_107(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)

    assessments = replace_assessment(
        assessments,
        RequirementAssessment(
            requirement_id="IA.L2-3.5.3",
            finding=AssessmentFinding.NOT_MET,
            implementation_state=(
                PartialImplementationState.PARTIALLY_IMPLEMENTED
            ),
        ),
    )

    result = engine.calculate(assessments)

    assert result.current_score == 107
    assert result.total_deduction_points == 3
    assert result.partial_credit_count == 1


def test_domain_scores_cover_14_domains(
    engine: ScoringEngine,
) -> None:
    result = engine.calculate(
        build_all_met_assessments(engine)
    )

    assert len(result.domain_scores) == 14

    assert {
        "AC",
        "AT",
        "AU",
        "CM",
        "IA",
        "IR",
        "MA",
        "MP",
        "PS",
        "PE",
        "RA",
        "CA",
        "SC",
        "SI",
    } == set(result.domain_scores)


def test_access_control_domain_summary(
    engine: ScoringEngine,
) -> None:
    result = engine.calculate(
        build_all_met_assessments(engine)
    )

    access_control = result.domain_scores["AC"]

    assert access_control.requirement_count == 22
    assert access_control.assessed_count == 22
    assert access_control.met_count == 22
    assert access_control.not_met_count == 0
    assert access_control.not_assessed_count == 0
    assert access_control.deduction_points == 0
    assert access_control.completion_percentage == 1.0


def test_missing_assessment_is_rejected_by_default(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)
    assessments.pop()

    with pytest.raises(
        ScoringEngineError,
        match="missing requirement IDs",
    ):
        engine.calculate(assessments)


def test_missing_assessment_can_default_to_not_assessed(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)
    assessments.pop()

    result = engine.calculate(
        assessments,
        require_all_requirements=False,
    )

    assert result.not_assessed_count == 1
    assert result.complete is False
    assert result.current_score == 110


def test_duplicate_assessment_is_rejected(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)
    assessments.append(assessments[0])

    with pytest.raises(
        ScoringEngineError,
        match="Duplicate assessment",
    ):
        engine.calculate(assessments)


def test_unknown_requirement_is_rejected(
    engine: ScoringEngine,
) -> None:
    assessments = build_all_met_assessments(engine)

    assessments[0] = RequirementAssessment(
        requirement_id="XX.L2-3.99.99",
        finding=AssessmentFinding.MET,
    )

    with pytest.raises(
        ScoringEngineError,
        match="unknown requirement IDs",
    ):
        engine.calculate(assessments)


def test_partial_requirement_requires_state_when_not_met(
    engine: ScoringEngine,
) -> None:
    with pytest.raises(
        ScoringEngineError,
        match="requires an implementation state",
    ):
        engine.score_requirement(
            RequirementAssessment(
                requirement_id="IA.L2-3.5.3",
                finding=AssessmentFinding.NOT_MET,
            )
        )


def test_fixed_requirement_rejects_partial_state(
    engine: ScoringEngine,
) -> None:
    with pytest.raises(
        ScoringEngineError,
        match="does not permit partial credit",
    ):
        engine.score_requirement(
            RequirementAssessment(
                requirement_id="AC.L2-3.1.1",
                finding=AssessmentFinding.NOT_MET,
                implementation_state=(
                    PartialImplementationState.PARTIALLY_IMPLEMENTED
                ),
            )
        )


def test_met_partial_requirement_rejects_partial_state(
    engine: ScoringEngine,
) -> None:
    with pytest.raises(
        ScoringEngineError,
        match="must be FULLY IMPLEMENTED",
    ):
        engine.score_requirement(
            RequirementAssessment(
                requirement_id="IA.L2-3.5.3",
                finding=AssessmentFinding.MET,
                implementation_state=(
                    PartialImplementationState.PARTIALLY_IMPLEMENTED
                ),
            )
        )


def test_non_applicable_requirement_rejects_met_finding(
    engine: ScoringEngine,
) -> None:
    with pytest.raises(
        ScoringEngineError,
        match="marked non-applicable",
    ):
        engine.score_requirement(
            RequirementAssessment(
                requirement_id="AC.L2-3.1.1",
                finding=AssessmentFinding.MET,
                applicable=False,
            )
        )


def test_requirement_id_alias_is_normalized(
    engine: ScoringEngine,
) -> None:
    result = engine.score_requirement(
        RequirementAssessment(
            requirement_id="ac-l2-3.1.1",
            finding="NOT MET",
        )
    )

    assert result.requirement_id == "AC.L2-3.1.1"
    assert result.deduction_points == 5