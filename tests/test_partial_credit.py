import pytest

from src.scoring.partial_credit import (
    AssessmentFinding,
    PARTIAL_CREDIT_RULES,
    PartialCreditError,
    PartialCreditEvaluator,
    PartialImplementationState,
)


@pytest.fixture
def evaluator() -> PartialCreditEvaluator:
    return PartialCreditEvaluator()


def test_supports_only_regulatory_partial_credit_requirements(
    evaluator: PartialCreditEvaluator,
) -> None:
    assert evaluator.supports("IA.L2-3.5.3")
    assert evaluator.supports("SC.L2-3.13.11")
    assert not evaluator.supports("AC.L2-3.1.1")


def test_partial_credit_rule_count() -> None:
    assert len(PARTIAL_CREDIT_RULES) == 2


def test_get_rule_for_mfa_requirement(
    evaluator: PartialCreditEvaluator,
) -> None:
    rule = evaluator.get_rule("IA.L2-3.5.3")

    assert rule.requirement_id == "IA.L2-3.5.3"
    assert rule.partial_deduction_points == 3
    assert rule.full_deduction_points == 5
    assert "Multi-factor authentication" in rule.partial_condition


def test_get_rule_for_encryption_requirement(
    evaluator: PartialCreditEvaluator,
) -> None:
    rule = evaluator.get_rule("SC.L2-3.13.11")

    assert rule.requirement_id == "SC.L2-3.13.11"
    assert rule.partial_deduction_points == 3
    assert rule.full_deduction_points == 5
    assert "Encryption" in rule.partial_condition


def test_get_rule_rejects_unsupported_requirement(
    evaluator: PartialCreditEvaluator,
) -> None:
    with pytest.raises(
        PartialCreditError,
        match="Partial credit is not permitted",
    ):
        evaluator.get_rule("AC.L2-3.1.1")


@pytest.mark.parametrize(
    ("requirement_id", "finding", "state"),
    [
        (
            "IA.L2-3.5.3",
            AssessmentFinding.MET,
            PartialImplementationState.FULLY_IMPLEMENTED,
        ),
        (
            "SC.L2-3.13.11",
            AssessmentFinding.MET,
            PartialImplementationState.FULLY_IMPLEMENTED,
        ),
    ],
)
def test_met_requirement_has_zero_deduction(
    evaluator: PartialCreditEvaluator,
    requirement_id: str,
    finding: AssessmentFinding,
    state: PartialImplementationState,
) -> None:
    result = evaluator.evaluate(
        requirement_id=requirement_id,
        finding=finding,
        implementation_state=state,
    )

    assert result.deduction_points == 0
    assert result.partial_credit_applied is False
    assert result.finding == AssessmentFinding.MET


@pytest.mark.parametrize(
    "requirement_id",
    [
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    ],
)
def test_not_applicable_has_zero_deduction(
    evaluator: PartialCreditEvaluator,
    requirement_id: str,
) -> None:
    result = evaluator.evaluate(
        requirement_id=requirement_id,
        finding="NOT APPLICABLE",
        implementation_state="NOT APPLICABLE",
    )

    assert result.deduction_points == 0
    assert result.partial_credit_applied is False


@pytest.mark.parametrize(
    "requirement_id",
    [
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    ],
)
def test_not_assessed_has_zero_current_deduction(
    evaluator: PartialCreditEvaluator,
    requirement_id: str,
) -> None:
    result = evaluator.evaluate(
        requirement_id=requirement_id,
        finding="NOT ASSESSED",
        implementation_state="NOT ASSESSED",
    )

    assert result.deduction_points == 0
    assert result.partial_credit_applied is False


@pytest.mark.parametrize(
    "requirement_id",
    [
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    ],
)
def test_partial_implementation_deducts_three_points(
    evaluator: PartialCreditEvaluator,
    requirement_id: str,
) -> None:
    result = evaluator.evaluate(
        requirement_id=requirement_id,
        finding="NOT MET",
        implementation_state="PARTIALLY IMPLEMENTED",
    )

    assert result.deduction_points == 3
    assert result.partial_credit_applied is True
    assert result.finding == AssessmentFinding.NOT_MET


@pytest.mark.parametrize(
    "requirement_id",
    [
        "IA.L2-3.5.3",
        "SC.L2-3.13.11",
    ],
)
def test_not_implemented_deducts_five_points(
    evaluator: PartialCreditEvaluator,
    requirement_id: str,
) -> None:
    result = evaluator.evaluate(
        requirement_id=requirement_id,
        finding="NOT MET",
        implementation_state="NOT IMPLEMENTED",
    )

    assert result.deduction_points == 5
    assert result.partial_credit_applied is False


def test_deduction_for_returns_integer(
    evaluator: PartialCreditEvaluator,
) -> None:
    deduction = evaluator.deduction_for(
        requirement_id="IA.L2-3.5.3",
        finding="NOT MET",
        implementation_state="PARTIAL",
    )

    assert deduction == 3
    assert isinstance(deduction, int)


def test_requirement_id_normalization(
    evaluator: PartialCreditEvaluator,
) -> None:
    result = evaluator.evaluate(
        requirement_id="ia-l2-3.5.3",
        finding="not met",
        implementation_state="partial",
    )

    assert result.requirement_id == "IA.L2-3.5.3"
    assert result.deduction_points == 3


@pytest.mark.parametrize(
    ("finding", "state"),
    [
        ("MET", "PARTIALLY IMPLEMENTED"),
        ("MET", "NOT IMPLEMENTED"),
        ("NOT APPLICABLE", "FULLY IMPLEMENTED"),
        ("NOT ASSESSED", "PARTIALLY IMPLEMENTED"),
        ("NOT MET", "FULLY IMPLEMENTED"),
        ("NOT MET", "NOT APPLICABLE"),
    ],
)
def test_inconsistent_finding_state_combinations_are_rejected(
    evaluator: PartialCreditEvaluator,
    finding: str,
    state: str,
) -> None:
    with pytest.raises(PartialCreditError):
        evaluator.evaluate(
            requirement_id="IA.L2-3.5.3",
            finding=finding,
            implementation_state=state,
        )


def test_invalid_finding_is_rejected(
    evaluator: PartialCreditEvaluator,
) -> None:
    with pytest.raises(
        PartialCreditError,
        match="Unsupported assessment finding",
    ):
        evaluator.evaluate(
            requirement_id="IA.L2-3.5.3",
            finding="UNKNOWN",
            implementation_state="NOT IMPLEMENTED",
        )


def test_invalid_implementation_state_is_rejected(
    evaluator: PartialCreditEvaluator,
) -> None:
    with pytest.raises(
        PartialCreditError,
        match="Unsupported partial implementation state",
    ):
        evaluator.evaluate(
            requirement_id="IA.L2-3.5.3",
            finding="NOT MET",
            implementation_state="SOMEWHAT IMPLEMENTED",
        )


def test_unsupported_requirement_cannot_be_evaluated(
    evaluator: PartialCreditEvaluator,
) -> None:
    with pytest.raises(
        PartialCreditError,
        match="Partial credit is not permitted",
    ):
        evaluator.evaluate(
            requirement_id="AC.L2-3.1.1",
            finding="NOT MET",
            implementation_state="NOT IMPLEMENTED",
        )


def test_mfa_partial_result_explanation(
    evaluator: PartialCreditEvaluator,
) -> None:
    result = evaluator.evaluate(
        requirement_id="IA.L2-3.5.3",
        finding="NOT MET",
        implementation_state="PARTIALLY IMPLEMENTED",
    )

    assert "Multi-factor authentication" in result.explanation
    assert "3 points are deducted" in result.explanation


def test_encryption_full_deduction_explanation(
    evaluator: PartialCreditEvaluator,
) -> None:
    result = evaluator.evaluate(
        requirement_id="SC.L2-3.13.11",
        finding="NOT MET",
        implementation_state="NOT IMPLEMENTED",
    )

    assert "Encryption is not employed" in result.explanation
    assert "5 points are deducted" in result.explanation