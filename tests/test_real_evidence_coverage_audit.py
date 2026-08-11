from __future__ import annotations

from pathlib import Path

import pytest

from src.evidence_requests.assessment_procedure_loader import (
    AssessmentProcedureLoader,
)
from src.evidence_requests.catalog_compiler import CatalogCompiler
from src.evidence_requests.evidence_coverage_audit import EvidenceCoverageAuditor
from src.evidence_requests.request_generator import RequestGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_CANDIDATES = (
    PROJECT_ROOT / "data" / "sp800-171a-assessment-procedures.xlsx",
    PROJECT_ROOT / "docs" / "source" / "sp800-171a-assessment-procedures.xlsx",
)


def requirement_text_provider(requirement_id: str) -> str | None:
    fallback_requirements = {
        "SC.L2-3.13.12": (
            "Prohibit remote activation of collaborative computing devices "
            "and provide indication of devices in use to users present at the device."
        )
    }
    return fallback_requirements.get(requirement_id)


@pytest.fixture(scope="module")
def coverage_report():
    workbook = next(
        (candidate for candidate in WORKBOOK_CANDIDATES if candidate.is_file()),
        None,
    )
    if workbook is None:
        pytest.fail("Unable to locate the SP 800-171A assessment-procedure workbook.")

    dataset = AssessmentProcedureLoader(
        framework_id="CMMC_L2",
        framework_name="CMMC Level 2",
        framework_version="2.0",
        source_document="NIST SP 800-171A",
        requirement_text_provider=requirement_text_provider,
    ).load(workbook)
    knowledge = CatalogCompiler().compile(dataset.rows)
    raw_drl = RequestGenerator().generate(knowledge, framework_id="CMMC_L2")

    return EvidenceCoverageAuditor().audit(raw_drl, knowledge=knowledge)


def test_real_audit_covers_the_complete_generated_drl(coverage_report) -> None:
    assert coverage_report.total_requests == 297
    assert len(coverage_report.entries) == 297


def test_real_audit_preserves_control_and_objective_traceability(
    coverage_report,
) -> None:
    assert all(entry.control_ids for entry in coverage_report.entries)
    assert (
        coverage_report.objective_traced_requests
        + coverage_report.missing_objective_trace
        == coverage_report.total_requests
    )
    assert coverage_report.objective_traced_requests > 0


def test_real_audit_totals_are_consistent(coverage_report) -> None:
    assert (
        coverage_report.canonical_matches
        + coverage_report.alias_matches
        + coverage_report.curated_mappings
        + coverage_report.classified_non_evidence
        + coverage_report.unresolved
        == coverage_report.total_requests
    )
    assert (
        coverage_report.resolved
        + coverage_report.classified_non_evidence
        + coverage_report.unresolved
        == 297
    )


def test_print_real_evidence_coverage(coverage_report) -> None:
    print()
    print("REAL SP 800-171A GENERATED EVIDENCE COVERAGE")
    print(f"Generated requests: {coverage_report.total_requests}")
    print(f"Canonical matches:  {coverage_report.canonical_matches}")
    print(f"Alias matches:      {coverage_report.alias_matches}")
    print(f"Curated mappings:   {coverage_report.curated_mappings}")
    print(f"Classified non-EV:  {coverage_report.classified_non_evidence}")
    print(f"Unresolved:         {coverage_report.unresolved}")
    print(f"Coverage:           {coverage_report.coverage_percent:.2f}%")
    print(f"Classified:         {coverage_report.classification_percent:.2f}%")
    print(
        "Objective trace:    "
        f"{coverage_report.objective_traced_requests}/"
        f"{coverage_report.total_requests} "
        f"({coverage_report.objective_trace_percent:.2f}%)"
    )
    print("Unresolved titles:")
    for title in coverage_report.unresolved_titles:
        print(f"- {title}")

    assert True
