from datetime import date
from pathlib import Path

import pytest

from src.assessment import (
    AssessmentEngine,
    AssessmentEngineError,
    AssessmentMetadata,
    EvidenceReference,
    EvidenceStatus,
    ObjectiveFinding,
    POAMStatus,
)
from src.scoring import (
    AssessmentFinding,
    PartialImplementationState,
)


ROOT = Path(__file__).resolve().parents[1]

CONTROLS_PATH = (
    ROOT
    / "data"
    / "controls"
    / "cmmc_level2_controls.csv"
)

OBJECTIVES_PATH = (
    ROOT
    / "data"
    / "controls"
    / "cmmc_level2_objectives.csv"
)

SCORING_WEIGHTS_PATH = (
    ROOT
    / "data"
    / "scoring"
    / "scoring_weights.csv"
)


@pytest.fixture
def engine() -> AssessmentEngine:
    return AssessmentEngine(
        controls_csv=CONTROLS_PATH,
        objectives_csv=OBJECTIVES_PATH,
        scoring_weights_csv=SCORING_WEIGHTS_PATH,
    )


@pytest.fixture
def assessment(engine: AssessmentEngine):
    metadata = AssessmentMetadata(
        assessment_id="TEST-001",
        organization_name="Test Organization",
        assessment_name="Initial CMMC Assessment",
        cage_code="1A2B3",
        scope="CUI enclave",
        lead_assessor="Test Assessor",
    )

    return engine.create_assessment(metadata)


def test_engine_creates_110_requirements(
    assessment,
) -> None:
    assert assessment.requirement_count == 110
    assert len(assessment.requirements) == 110


def test_new_assessment_is_zero_percent_complete(
    assessment,
) -> None:
    assert assessment.assessed_requirement_count == 0
    assert assessment.completion_percentage == 0.0


def test_first_requirement_exists(
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    assert record.requirement_id == "AC.L2-3.1.1"
    assert record.finding == AssessmentFinding.NOT_ASSESSED
    assert record.assessed is False


def test_first_requirement_has_six_objectives(
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    assert record.objective_count == 6

    assert [
        objective.objective_id
        for objective in record.objective_assessments
    ] == [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
    ]


def test_partial_credit_requirement_has_default_state(
    assessment,
) -> None:
    record = assessment.get_requirement(
        "IA.L2-3.5.3"
    )

    assert record.implementation_state == (
        PartialImplementationState.NOT_ASSESSED
    )


def test_fixed_requirement_has_no_partial_state(
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    assert record.implementation_state is None


def test_update_requirement_to_met(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = engine.update_requirement(
        assessment,
        "AC.L2-3.1.1",
        finding="MET",
        evidence_status="COMPLETE",
        control_owner="Security Manager",
        assessor="Lead Assessor",
        assessment_date=date(2026, 8, 4),
        ssp_reference="SSP Section 3.1.1",
        policy_reference="Access Control Policy",
        procedure_reference="Account Management Procedure",
        assessor_notes="Requirement implemented and verified.",
    )

    assert record.finding == AssessmentFinding.MET
    assert record.evidence_status == EvidenceStatus.COMPLETE
    assert record.control_owner == "Security Manager"
    assert record.assessment_date == date(2026, 8, 4)
    assert record.poam_status == POAMStatus.NOT_REQUIRED
    assert record.assessed is True


def test_update_requirement_to_not_met_opens_poam(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = engine.update_requirement(
        assessment,
        "AC.L2-3.1.1",
        finding="NOT MET",
        evidence_status="IN PROGRESS",
        assessor_notes="Access restrictions are incomplete.",
    )

    assert record.finding == AssessmentFinding.NOT_MET
    assert record.poam_status == POAMStatus.OPEN
    assert assessment.open_poam_count == 1


def test_changing_not_met_to_met_closes_poam_requirement(
    engine: AssessmentEngine,
    assessment,
) -> None:
    engine.update_requirement(
        assessment,
        "AC.L2-3.1.1",
        finding="NOT MET",
    )

    record = engine.update_requirement(
        assessment,
        "AC.L2-3.1.1",
        finding="MET",
    )

    assert record.poam_status == POAMStatus.NOT_REQUIRED
    assert record.poam_id == ""
    assert assessment.open_poam_count == 0


def test_partial_credit_requirement_can_be_partially_implemented(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = engine.update_requirement(
        assessment,
        "IA.L2-3.5.3",
        finding="NOT MET",
        implementation_state="PARTIALLY IMPLEMENTED",
    )

    assert record.finding == AssessmentFinding.NOT_MET
    assert record.implementation_state == (
        PartialImplementationState.PARTIALLY_IMPLEMENTED
    )
    assert record.poam_status == POAMStatus.OPEN


def test_partial_credit_requirement_requires_state(
    engine: AssessmentEngine,
    assessment,
) -> None:
    with pytest.raises(
        AssessmentEngineError,
        match="requires an implementation state",
    ):
        engine.update_requirement(
            assessment,
            "IA.L2-3.5.3",
            finding="NOT MET",
            implementation_state=None,
        )


def test_fixed_requirement_rejects_partial_state(
    engine: AssessmentEngine,
    assessment,
) -> None:
    with pytest.raises(
        AssessmentEngineError,
        match="does not permit partial credit",
    ):
        engine.update_requirement(
            assessment,
            "AC.L2-3.1.1",
            finding="NOT MET",
            implementation_state="PARTIALLY IMPLEMENTED",
        )


def test_add_evidence(
    engine: AssessmentEngine,
    assessment,
) -> None:
    evidence = EvidenceReference(
        evidence_id="EV-001",
        title="Access Control Policy",
        evidence_type="Policy",
        location="SharePoint/Policies/AC-Policy.pdf",
        owner="Security Manager",
        reviewed=True,
    )

    engine.add_evidence(
        assessment,
        evidence,
    )

    assert "EV-001" in assessment.evidence_register

    stored = assessment.evidence_register["EV-001"]

    assert stored.title == "Access Control Policy"
    assert stored.reviewed is True


def test_duplicate_evidence_is_rejected(
    engine: AssessmentEngine,
    assessment,
) -> None:
    evidence = EvidenceReference(
        evidence_id="EV-001",
        title="Access Control Policy",
    )

    engine.add_evidence(
        assessment,
        evidence,
    )

    with pytest.raises(
        ValueError,
        match="Duplicate evidence ID",
    ):
        engine.add_evidence(
            assessment,
            evidence,
        )


def test_link_evidence_to_requirement(
    engine: AssessmentEngine,
    assessment,
) -> None:
    engine.add_evidence(
        assessment,
        EvidenceReference(
            evidence_id="EV-001",
            title="Access Control Policy",
        ),
    )

    engine.add_evidence(
        assessment,
        EvidenceReference(
            evidence_id="EV-002",
            title="Authorized User Listing",
        ),
    )

    engine.link_evidence_to_requirement(
        assessment,
        "AC.L2-3.1.1",
        [
            "EV-001",
            "EV-002",
            "EV-001",
        ],
    )

    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    assert record.evidence_ids == [
        "EV-001",
        "EV-002",
    ]

    assert record.evidence_status == (
        EvidenceStatus.IN_PROGRESS
    )


def test_unknown_evidence_cannot_be_linked(
    engine: AssessmentEngine,
    assessment,
) -> None:
    with pytest.raises(
        AssessmentEngineError,
        match="Unknown evidence ID",
    ):
        engine.link_evidence_to_requirement(
            assessment,
            "AC.L2-3.1.1",
            ["EV-999"],
        )


def test_update_objective(
    engine: AssessmentEngine,
    assessment,
) -> None:
    objective = engine.update_objective(
        assessment,
        "AC.L2-3.1.1",
        "a",
        finding="SATISFIED",
        assessor_notes="Authorized users are documented.",
    )

    assert objective.objective_id == "a"
    assert objective.finding == ObjectiveFinding.SATISFIED
    assert objective.assessed is True
    assert objective.satisfied is True


def test_update_objective_with_evidence(
    engine: AssessmentEngine,
    assessment,
) -> None:
    engine.add_evidence(
        assessment,
        EvidenceReference(
            evidence_id="EV-001",
            title="Authorized User Listing",
        ),
    )

    objective = engine.update_objective(
        assessment,
        "AC.L2-3.1.1",
        "a",
        finding="SATISFIED",
        evidence_ids=["EV-001"],
    )

    assert objective.evidence_ids == ["EV-001"]


def test_unknown_objective_is_rejected(
    engine: AssessmentEngine,
    assessment,
) -> None:
    with pytest.raises(
        AssessmentEngineError,
        match="does not exist",
    ):
        engine.update_objective(
            assessment,
            "AC.L2-3.1.1",
            "z",
            finding="SATISFIED",
        )


def test_all_satisfied_objectives_make_requirement_met(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    for objective in record.objective_assessments:
        engine.update_objective(
            assessment,
            record.requirement_id,
            objective.objective_id,
            finding="SATISFIED",
        )

    result = (
        engine.synchronize_requirement_from_objectives(
            assessment,
            record.requirement_id,
        )
    )

    assert result.finding == AssessmentFinding.MET
    assert result.all_objectives_satisfied is True
    assert result.poam_status == POAMStatus.NOT_REQUIRED


def test_one_failed_objective_makes_requirement_not_met(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    for objective in record.objective_assessments:
        finding = (
            "NOT SATISFIED"
            if objective.objective_id == "c"
            else "SATISFIED"
        )

        engine.update_objective(
            assessment,
            record.requirement_id,
            objective.objective_id,
            finding=finding,
        )

    result = (
        engine.synchronize_requirement_from_objectives(
            assessment,
            record.requirement_id,
        )
    )

    assert result.finding == AssessmentFinding.NOT_MET
    assert result.poam_status == POAMStatus.OPEN


def test_unassessed_objective_keeps_requirement_unassessed(
    engine: AssessmentEngine,
    assessment,
) -> None:
    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    engine.update_objective(
        assessment,
        record.requirement_id,
        "a",
        finding="SATISFIED",
    )

    result = (
        engine.synchronize_requirement_from_objectives(
            assessment,
            record.requirement_id,
        )
    )

    assert result.finding == (
        AssessmentFinding.NOT_ASSESSED
    )


def test_calculate_new_assessment_score(
    engine: AssessmentEngine,
    assessment,
) -> None:
    score = engine.calculate_score(
        assessment
    )

    assert score.requirement_count == 110
    assert score.current_score == 110
    assert score.not_assessed_count == 110
    assert score.complete is False


def test_calculate_score_with_five_point_failure(
    engine: AssessmentEngine,
    assessment,
) -> None:
    for requirement_id in assessment.requirements:
        scoring_rule = (
            engine.scoring_engine.get_rule(
                requirement_id
            )
        )

        engine.update_requirement(
            assessment,
            requirement_id,
            finding="MET",
            implementation_state=(
                "FULLY IMPLEMENTED"
                if scoring_rule.partial_credit_allowed
                else None
            ),
        )

    engine.update_requirement(
        assessment,
        "AC.L2-3.1.1",
        finding="NOT MET",
    )

    score = engine.calculate_score(
        assessment
    )

    assert score.current_score == 105
    assert score.total_deduction_points == 5
    assert score.not_met_count == 1
    assert score.complete is True


def test_calculate_score_with_partial_credit(
    engine: AssessmentEngine,
    assessment,
) -> None:
    for requirement_id in assessment.requirements:
        scoring_rule = (
            engine.scoring_engine.get_rule(
                requirement_id
            )
        )

        engine.update_requirement(
            assessment,
            requirement_id,
            finding="MET",
            implementation_state=(
                "FULLY IMPLEMENTED"
                if scoring_rule.partial_credit_allowed
                else None
            ),
        )

    engine.update_requirement(
        assessment,
        "IA.L2-3.5.3",
        finding="NOT MET",
        implementation_state="PARTIALLY IMPLEMENTED",
    )

    score = engine.calculate_score(
        assessment
    )

    assert score.current_score == 107
    assert score.total_deduction_points == 3
    assert score.partial_credit_count == 1


def test_unknown_requirement_is_rejected(
    assessment,
) -> None:
    with pytest.raises(
        KeyError,
        match="Requirement not found",
    ):
        assessment.get_requirement(
            "XX.L2-3.99.99"
        )