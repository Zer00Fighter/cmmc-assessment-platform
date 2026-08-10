from __future__ import annotations

from pathlib import Path

import pytest

from src.evidence_requests.assessment_procedure_loader import (
    AssessmentProcedureDataset,
    AssessmentProcedureLoader,
)
from src.evidence_requests.catalog_compiler import (
    CatalogCompiler,
)
from src.evidence_requests.drl_model import (
    DocumentationRequestCollection,
    DocumentationRequestPriority,
)
from src.evidence_requests.request_generator import (
    RequestGenerator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WORKBOOK_CANDIDATES = (
    PROJECT_ROOT
    / "data"
    / "sp800-171a-assessment-procedures.xlsx",
    PROJECT_ROOT
    / "docs"
    / "source"
    / "sp800-171a-assessment-procedures.xlsx",
)


def requirement_text_provider(
    requirement_id: str,
) -> str | None:
    """
    Known source-data fallback.

    The parsed SP 800-171A workbook contains a blank Security Requirement
    cell for SC.L2-3.13.12. Keep that source anomaly outside the loader.
    """

    fallback_requirements = {
        "SC.L2-3.13.12": (
            "Prohibit remote activation of collaborative "
            "computing devices and provide indication of "
            "devices in use to users present at the device."
        ),
    }

    return fallback_requirements.get(
        requirement_id
    )


@pytest.fixture(scope="module")
def real_workbook() -> Path:
    for candidate in WORKBOOK_CANDIDATES:
        if candidate.is_file():
            return candidate

    expected = "\n".join(
        str(path)
        for path in WORKBOOK_CANDIDATES
    )

    pytest.fail(
        "Unable to locate "
        "sp800-171a-assessment-procedures.xlsx.\n"
        "Expected one of:\n"
        f"{expected}"
    )


@pytest.fixture(scope="module")
def dataset(
    real_workbook: Path,
) -> AssessmentProcedureDataset:
    loader = AssessmentProcedureLoader(
        framework_id="CMMC_L2",
        framework_name="CMMC Level 2",
        framework_version="2.0",
        source_document="NIST SP 800-171A",
        requirement_text_provider=(
            requirement_text_provider
        ),
    )

    return loader.load(
        real_workbook
    )


@pytest.fixture(scope="module")
def compiled_knowledge(
    dataset: AssessmentProcedureDataset,
):
    return CatalogCompiler().compile(
        dataset.rows
    )


@pytest.fixture(scope="module")
def real_drl(
    compiled_knowledge,
) -> DocumentationRequestCollection:
    return RequestGenerator().generate(
        compiled_knowledge,
        framework_id="CMMC_L2",
        engagement_name=(
            "Real SP 800-171A DRL Integration Test"
        ),
        organization_name=(
            "Integration Test Organization"
        ),
    )


def test_real_request_generator_returns_collection(
    real_drl: DocumentationRequestCollection,
) -> None:
    assert isinstance(
        real_drl,
        DocumentationRequestCollection,
    )

    assert real_drl.framework_id == "CMMC_L2"

    assert real_drl.count > 0


def test_real_request_generator_produces_unique_ids(
    real_drl: DocumentationRequestCollection,
) -> None:
    request_ids = [
        request.request_id
        for request in real_drl.requests
    ]

    assert len(request_ids) == len(
        set(
            value.casefold()
            for value in request_ids
        )
    )


def test_real_request_generator_uses_canonical_control_ids(
    real_drl: DocumentationRequestCollection,
) -> None:
    for request in real_drl.requests:
        assert request.controls

        for control in request.controls:
            assert ".L2-" in control.control_id
            assert control.framework_id == "CMMC_L2"


def test_real_request_generator_maps_known_control(
    real_drl: DocumentationRequestCollection,
) -> None:
    mapped_controls = {
        control.control_id
        for request in real_drl.requests
        for control in request.controls
    }

    assert "AC.L2-3.1.1" in mapped_controls
    assert "SC.L2-3.13.12" in mapped_controls


def test_real_request_generator_preserves_reuse(
    real_drl: DocumentationRequestCollection,
) -> None:
    reused = [
        request
        for request in real_drl.requests
        if request.is_reused
    ]

    assert reused


def test_real_request_generator_has_priority_distribution(
    real_drl: DocumentationRequestCollection,
) -> None:
    priorities = {
        request.priority
        for request in real_drl.requests
    }

    assert DocumentationRequestPriority.LOW in priorities

    assert (
        DocumentationRequestPriority.MEDIUM
        in priorities
        or DocumentationRequestPriority.HIGH
        in priorities
    )


def test_real_request_generator_summary_is_consistent(
    real_drl: DocumentationRequestCollection,
) -> None:
    summary = real_drl.summary

    assert summary.total_requests == real_drl.count

    assert (
        summary.high_priority
        + summary.medium_priority
        + summary.low_priority
        == real_drl.count
    )

    assert (
        summary.total_control_mappings
        >= summary.unique_controls_supported
    )

    assert (
        summary.reused_requests
        <= summary.total_requests
    )


def test_real_request_generator_supports_many_controls(
    real_drl: DocumentationRequestCollection,
) -> None:
    summary = real_drl.summary

    assert summary.unique_controls_supported >= 100


def test_real_request_generator_has_no_empty_requested_items(
    real_drl: DocumentationRequestCollection,
) -> None:
    for request in real_drl.requests:
        assert request.requested_item.strip()


def test_print_real_drl_statistics(
    dataset: AssessmentProcedureDataset,
    compiled_knowledge,
    real_drl: DocumentationRequestCollection,
) -> None:
    knowledge_stats = (
        compiled_knowledge.statistics
    )

    drl_summary = real_drl.summary

    print()
    print(
        "========================================"
    )
    print(
        "REAL SP 800-171A DRL GENERATION"
    )
    print(
        "========================================"
    )

    print(
        f"Loader rows:             "
        f"{dataset.row_count}"
    )

    print(
        f"Requirements:            "
        f"{dataset.requirement_count}"
    )

    print(
        f"Objectives:              "
        f"{dataset.objective_count}"
    )

    print(
        f"Compiled evidence:       "
        f"{knowledge_stats.evidence_count}"
    )

    print(
        f"Generated DRL requests:  "
        f"{drl_summary.total_requests}"
    )

    print(
        f"Unique controls covered: "
        f"{drl_summary.unique_controls_supported}"
    )

    print(
        f"Control mappings:        "
        f"{drl_summary.total_control_mappings}"
    )

    print(
        f"Reused DRL requests:     "
        f"{drl_summary.reused_requests}"
    )

    print(
        f"High priority:           "
        f"{drl_summary.high_priority}"
    )

    print(
        f"Medium priority:         "
        f"{drl_summary.medium_priority}"
    )

    print(
        f"Low priority:            "
        f"{drl_summary.low_priority}"
    )

    print()
    print(
        "TOP 20 REUSED DRL REQUESTS"
    )
    print(
        "----------------------------------------"
    )

    reused = sorted(
        real_drl.requests,
        key=lambda request: (
            -request.reuse_count,
            request.requested_item.casefold(),
        ),
    )

    for request in reused[:20]:
        print(
            f"{request.reuse_count:>3} controls  "
            f"{request.request_id:<8} "
            f"{request.requested_item}"
        )

    print(
        "========================================"
    )

    assert True