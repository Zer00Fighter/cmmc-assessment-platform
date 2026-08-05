from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.assessment import (
    AssessmentEngine,
    AssessmentMetadata,
    AssessmentStatus,
    AssessmentValidationError,
    AssessmentValidator,
    EvidenceReference,
    EvidenceStatus,
    ObjectiveFinding,
    POAMStatus,
)
from src.scoring import (
    AssessmentFinding,
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
def validator(
    engine: AssessmentEngine,
) -> AssessmentValidator:
    return AssessmentValidator(
        assessment_engine=engine
    )


@pytest.fixture
def draft_assessment(
    engine: AssessmentEngine,
):
    metadata = AssessmentMetadata(
        assessment_id="VAL-001",
        organization_name="Test Organization",
        assessment_name="Validation Test",
        cage_code="1A2B3",
        scope="CUI enclave",
        lead_assessor="Lead Assessor",
        assessment_start_date=date(2026, 8, 1),
        assessment_end_date=date(2026, 8, 4),
        status=AssessmentStatus.DRAFT,
    )

    return engine.create_assessment(metadata)


def complete_all_objectives(
    engine: AssessmentEngine,
    assessment,
) -> None:
    for requirement_id, record in (
        assessment.requirements.items()
    ):
        for objective in record.objective_assessments:
            engine.update_objective(
                assessment,
                requirement_id,
                objective.objective_id,
                finding=ObjectiveFinding.SATISFIED,
            )


def mark_all_requirements_met(
    engine: AssessmentEngine,
    assessment,
    *,
    evidence_status: EvidenceStatus = (
        EvidenceStatus.NOT_STARTED
    ),
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
            finding=AssessmentFinding.MET,
            implementation_state=(
                "FULLY IMPLEMENTED"
                if scoring_rule.partial_credit_allowed
                else None
            ),
            evidence_status=evidence_status,
            assessor="Lead Assessor",
            assessment_date=date(2026, 8, 4),
        )


def add_reviewed_evidence_to_every_requirement(
    engine: AssessmentEngine,
    assessment,
) -> None:
    for index, requirement_id in enumerate(
        assessment.requirements,
        start=1,
    ):
        evidence_id = f"EV-{index:03d}"

        engine.add_evidence(
            assessment,
            EvidenceReference(
                evidence_id=evidence_id,
                title=(
                    f"Evidence for {requirement_id}"
                ),
                evidence_type="Document",
                location=(
                    f"Evidence/{evidence_id}.pdf"
                ),
                owner="Security Team",
                reviewed=True,
            ),
        )

        engine.link_evidence_to_requirement(
            assessment,
            requirement_id,
            [evidence_id],
        )

        assessment.get_requirement(
            requirement_id
        ).evidence_status = (
            EvidenceStatus.COMPLETE
        )


def build_ready_assessment(
    engine: AssessmentEngine,
):
    metadata = AssessmentMetadata(
        assessment_id="READY-001",
        organization_name="Test Organization",
        assessment_name="Ready Assessment",
        cage_code="1A2B3",
        scope="CUI enclave",
        lead_assessor="Lead Assessor",
        assessment_start_date=date(2026, 8, 1),
        assessment_end_date=date(2026, 8, 4),
        status=AssessmentStatus.READY_FOR_REVIEW,
    )

    assessment = engine.create_assessment(metadata)

    complete_all_objectives(
        engine,
        assessment,
    )

    mark_all_requirements_met(
        engine,
        assessment,
    )

    return assessment


def build_final_assessment(
    engine: AssessmentEngine,
):
    metadata = AssessmentMetadata(
        assessment_id="FINAL-001",
        organization_name="Test Organization",
        assessment_name="Final Assessment",
        cage_code="1A2B3",
        scope="CUI enclave",
        lead_assessor="Lead Assessor",
        assessment_start_date=date(2026, 8, 1),
        assessment_end_date=date(2026, 8, 4),
        status=AssessmentStatus.FINAL,
    )

    assessment = engine.create_assessment(metadata)

    complete_all_objectives(
        engine,
        assessment,
    )

    mark_all_requirements_met(
        engine,
        assessment,
    )

    add_reviewed_evidence_to_every_requirement(
        engine,
        assessment,
    )

    return assessment


def issue_codes(report) -> set[str]:
    return {
        issue.code
        for issue in report.errors
    }


def warning_codes(report) -> set[str]:
    return {
        issue.code
        for issue in report.warnings
    }


def test_draft_assessment_structure_passes(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    report = validator.validate(
        draft_assessment
    )

    assert report.passed
    assert report.error_count == 0
    assert report.requirement_count == 110
    assert report.assessed_requirement_count == 0
    assert report.current_score == 110
    assert report.score_complete is False
    assert "PROVISIONAL_SCORE" in warning_codes(
        report
    )


def test_ready_assessment_passes(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert report.passed
    assert report.error_count == 0
    assert report.current_score == 110
    assert report.score_complete is True


def test_final_assessment_passes(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_final_assessment(
        engine
    )

    report = validator.validate_final(
        assessment
    )

    assert report.passed
    assert report.error_count == 0
    assert report.current_score == 110
    assert report.score_complete is True
    assert report.evidence_count == 110


def test_ready_review_rejects_unassessed_requirements(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    report = (
        validator.validate_ready_for_review(
            draft_assessment
        )
    )

    codes = issue_codes(report)

    assert not report.passed
    assert "REQUIREMENT_NOT_ASSESSED" in codes
    assert "OBJECTIVE_NOT_ASSESSED" in codes
    assert "INCOMPLETE_SCORE" in codes


def test_ready_review_requires_scope(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        scope="",
    )

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert "MISSING_SCOPE" in issue_codes(
        report
    )


def test_ready_review_requires_lead_assessor(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        lead_assessor="",
    )

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert (
        "MISSING_LEAD_ASSESSOR"
        in issue_codes(report)
    )


def test_ready_review_requires_start_date(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        assessment_start_date=None,
    )

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert "MISSING_START_DATE" in issue_codes(
        report
    )


def test_final_requires_end_date(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_final_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        assessment_end_date=None,
    )

    report = validator.validate_final(
        assessment
    )

    assert "MISSING_END_DATE" in issue_codes(
        report
    )


def test_final_rejects_invalid_date_range(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_final_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        assessment_start_date=date(
            2026,
            8,
            5,
        ),
        assessment_end_date=date(
            2026,
            8,
            4,
        ),
    )

    report = validator.validate_final(
        assessment
    )

    assert "INVALID_DATE_RANGE" in issue_codes(
        report
    )


def test_missing_requirement_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    draft_assessment.requirements.pop(
        "SI.L2-3.14.7"
    )

    report = validator.validate(
        draft_assessment
    )

    codes = issue_codes(report)

    assert "REQUIREMENT_COUNT" in codes
    assert "MISSING_REQUIREMENT" in codes


def test_unexpected_requirement_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    original = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    draft_assessment.requirements[
        "XX.L2-3.99.99"
    ] = replace(
        original,
        requirement_id="XX.L2-3.99.99",
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "UNEXPECTED_REQUIREMENT"
        in issue_codes(report)
    )


def test_requirement_key_record_mismatch_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.requirement_id = "AC.L2-3.1.2"

    report = validator.validate(
        draft_assessment
    )

    assert (
        "REQUIREMENT_ID_MISMATCH"
        in issue_codes(report)
    )


def test_non_applicable_finding_mismatch_is_rejected(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.applicable = True
    record.finding = (
        AssessmentFinding.NOT_APPLICABLE
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "APPLICABILITY_MISMATCH"
        in issue_codes(report)
    )


def test_invalid_partial_state_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "IA.L2-3.5.3"
    )

    record.finding = AssessmentFinding.NOT_MET
    record.implementation_state = (
        None
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "INVALID_PARTIAL_STATE"
        in issue_codes(report)
    )


def test_fixed_requirement_rejects_partial_state(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.implementation_state = (
        "PARTIALLY IMPLEMENTED"
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "UNEXPECTED_IMPLEMENTATION_STATE"
        in issue_codes(report)
    )


def test_duplicate_objective_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.objective_assessments.append(
        record.objective_assessments[0]
    )

    report = validator.validate(
        draft_assessment
    )

    assert "DUPLICATE_OBJECTIVE" in issue_codes(
        report
    )


def test_missing_objective_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.objective_assessments.pop()

    report = validator.validate(
        draft_assessment
    )

    assert "MISSING_OBJECTIVE" in issue_codes(
        report
    )


def test_met_requirement_with_failed_objective_is_rejected(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    for objective in record.objective_assessments:
        objective.finding = (
            ObjectiveFinding.SATISFIED
        )

    record.objective_assessments[
        0
    ].finding = ObjectiveFinding.NOT_SATISFIED

    engine.update_requirement(
        draft_assessment,
        record.requirement_id,
        finding="MET",
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "MET_OBJECTIVE_MISMATCH"
        in issue_codes(report)
    )


def test_not_met_with_all_satisfied_objectives_warns(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    for objective in record.objective_assessments:
        objective.finding = (
            ObjectiveFinding.SATISFIED
        )

    engine.update_requirement(
        draft_assessment,
        record.requirement_id,
        finding="NOT MET",
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "NOT_MET_OBJECTIVE_MISMATCH"
        in warning_codes(report)
    )


def test_unknown_requirement_evidence_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.evidence_ids = ["EV-999"]

    report = validator.validate(
        draft_assessment
    )

    assert "UNKNOWN_EVIDENCE" in issue_codes(
        report
    )


def test_complete_status_without_evidence_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.evidence_status = (
        EvidenceStatus.COMPLETE
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "COMPLETE_WITHOUT_EVIDENCE"
        in issue_codes(report)
    )


def test_final_requires_complete_evidence(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    assessment.metadata = replace(
        assessment.metadata,
        status=AssessmentStatus.FINAL,
    )

    report = validator.validate_final(
        assessment
    )

    assert (
        "FINAL_EVIDENCE_INCOMPLETE"
        in issue_codes(report)
    )


def test_final_rejects_unreviewed_evidence(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_final_assessment(
        engine
    )

    first_evidence_id = next(
        iter(assessment.evidence_register)
    )

    original = assessment.evidence_register[
        first_evidence_id
    ]

    assessment.evidence_register[
        first_evidence_id
    ] = replace(
        original,
        reviewed=False,
    )

    report = validator.validate_final(
        assessment
    )

    assert "UNREVIEWED_EVIDENCE" in issue_codes(
        report
    )


def test_not_met_requirement_requires_poam(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    record = draft_assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    record.finding = AssessmentFinding.NOT_MET
    record.poam_status = POAMStatus.NOT_REQUIRED

    report = validator.validate(
        draft_assessment
    )

    assert "POAM_REQUIRED" in issue_codes(
        report
    )


def test_ready_not_met_requires_poam_id(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    engine.update_requirement(
        assessment,
        record.requirement_id,
        finding="NOT MET",
        assessor="Lead Assessor",
        assessment_date=date(2026, 8, 4),
    )

    record.poam_status = POAMStatus.OPEN
    record.poam_id = ""

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert "MISSING_POAM_ID" in issue_codes(
        report
    )


def test_ready_not_met_with_poam_id_passes_poam_check(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    record = assessment.get_requirement(
        "AC.L2-3.1.1"
    )

    engine.update_requirement(
        assessment,
        record.requirement_id,
        finding="NOT MET",
        assessor="Lead Assessor",
        assessment_date=date(2026, 8, 4),
    )

    record.poam_status = POAMStatus.OPEN
    record.poam_id = "POAM-001"

    report = (
        validator.validate_ready_for_review(
            assessment
        )
    )

    assert "MISSING_POAM_ID" not in issue_codes(
        report
    )


def test_evidence_without_location_warns(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    engine.add_evidence(
        draft_assessment,
        EvidenceReference(
            evidence_id="EV-001",
            title="Access Control Policy",
            location="",
        ),
    )

    report = validator.validate(
        draft_assessment
    )

    assert (
        "MISSING_EVIDENCE_LOCATION"
        in warning_codes(report)
    )


def test_assessed_draft_without_assessor_warns(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    engine.update_requirement(
        draft_assessment,
        "AC.L2-3.1.1",
        finding="MET",
        assessor="",
        assessment_date=None,
    )

    report = validator.validate(
        draft_assessment
    )

    warnings = warning_codes(report)

    assert (
        "MISSING_REQUIREMENT_ASSESSOR"
        in warnings
    )
    assert "MISSING_ASSESSMENT_DATE" in warnings


def test_validate_or_raise_raises(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    with pytest.raises(
        AssessmentValidationError,
        match="assessment validation failed",
    ):
        validator.validate_ready_for_review_or_raise(
            draft_assessment
        )


def test_validate_or_raise_accepts_ready_assessment(
    engine: AssessmentEngine,
    validator: AssessmentValidator,
) -> None:
    assessment = build_ready_assessment(
        engine
    )

    report = (
        validator.validate_ready_for_review_or_raise(
            assessment
        )
    )

    assert report.passed


def test_unknown_target_status_is_rejected(
    validator: AssessmentValidator,
    draft_assessment,
) -> None:
    with pytest.raises(
        AssessmentValidationError,
        match="Unsupported assessment status",
    ):
        validator.validate(
            draft_assessment,
            target_status="UNKNOWN",
        )