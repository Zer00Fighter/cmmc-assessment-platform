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
)
from src.evidence_requests.request_generator import (
    RequestGenerator,
)
from src.evidence_requests.request_optimizer import (
    RequestOptimizer,
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
def raw_drl(
    compiled_knowledge,
) -> DocumentationRequestCollection:
    return RequestGenerator().generate(
        compiled_knowledge,
        framework_id="CMMC_L2",
        engagement_name=(
            "Real SP 800-171A DRL Optimizer Integration Test"
        ),
        organization_name=(
            "Integration Test Organization"
        ),
    )


@pytest.fixture(scope="module")
def optimized_drl(
    raw_drl: DocumentationRequestCollection,
) -> DocumentationRequestCollection:
    return RequestOptimizer().optimize(
        raw_drl
    )


def test_real_optimizer_returns_collection(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    assert isinstance(
        optimized_drl,
        DocumentationRequestCollection,
    )

    assert optimized_drl.framework_id == "CMMC_L2"

    assert optimized_drl.count > 0


def test_real_optimizer_reduces_request_count(
    raw_drl: DocumentationRequestCollection,
    optimized_drl: DocumentationRequestCollection,
) -> None:
    assert optimized_drl.count < raw_drl.count


def test_real_optimizer_preserves_unique_control_coverage(
    raw_drl: DocumentationRequestCollection,
    optimized_drl: DocumentationRequestCollection,
) -> None:
    assert (
        optimized_drl.summary.unique_controls_supported
        == raw_drl.summary.unique_controls_supported
    )


def test_real_optimizer_preserves_all_control_keys(
    raw_drl: DocumentationRequestCollection,
    optimized_drl: DocumentationRequestCollection,
) -> None:
    raw_keys = {
        control.key
        for request in raw_drl.requests
        for control in request.controls
    }

    optimized_keys = {
        control.key
        for request in optimized_drl.requests
        for control in request.controls
    }

    assert optimized_keys == raw_keys


def test_real_optimizer_preserves_all_110_controls(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    assert (
        optimized_drl.summary.unique_controls_supported
        == 110
    )


def test_real_optimizer_generates_unique_request_ids(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    request_ids = [
        request.request_id
        for request in optimized_drl.requests
    ]

    assert len(request_ids) == len(
        {
            value.casefold()
            for value in request_ids
        }
    )


def test_real_optimizer_generates_sequential_request_ids(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    expected = [
        f"DRL-{index:03d}"
        for index in range(
            1,
            optimized_drl.count + 1,
        )
    ]

    actual = [
        request.request_id
        for request in optimized_drl.requests
    ]

    assert actual == expected


def test_real_optimizer_suppresses_generic_request_when_safe(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    titles = {
        request.requested_item.casefold()
        for request in optimized_drl.requests
    }

    assert (
        "other relevant documents or records"
        not in titles
    )


def test_real_optimizer_preserves_access_control_package(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    matching = [
        request
        for request in optimized_drl.requests
        if (
            request.requested_item.casefold()
            == (
                "Access Control Policy and Procedures"
                .casefold()
            )
        )
    ]

    assert matching

    assert matching[0].controls


def test_real_optimizer_does_not_mutate_raw_drl(
    raw_drl: DocumentationRequestCollection,
) -> None:
    assert raw_drl.count == 297

    assert (
        raw_drl.summary.unique_controls_supported
        == 110
    )


def test_print_real_optimizer_statistics(
    raw_drl: DocumentationRequestCollection,
    optimized_drl: DocumentationRequestCollection,
) -> None:
    raw_summary = raw_drl.summary
    optimized_summary = (
        optimized_drl.summary
    )

    reduction = (
        raw_summary.total_requests
        - optimized_summary.total_requests
    )

    reduction_percent = (
        0.0
        if raw_summary.total_requests == 0
        else (
            reduction
            / raw_summary.total_requests
            * 100
        )
    )

    raw_titles = {
        request.requested_item.casefold():
            request.requested_item
        for request in raw_drl.requests
    }

    optimized_titles = {
        request.requested_item.casefold():
            request.requested_item
        for request in optimized_drl.requests
    }

    removed_titles = sorted(
        (
            raw_titles[key]
            for key in (
                raw_titles.keys()
                - optimized_titles.keys()
            )
        ),
        key=str.casefold,
    )

    added_titles = sorted(
        (
            optimized_titles[key]
            for key in (
                optimized_titles.keys()
                - raw_titles.keys()
            )
        ),
        key=str.casefold,
    )

    print()
    print(
        "========================================"
    )
    print(
        "REAL SP 800-171A DRL OPTIMIZATION"
    )
    print(
        "========================================"
    )

    print(
        f"Raw DRL requests:        "
        f"{raw_summary.total_requests}"
    )

    print(
        f"Optimized DRL requests:  "
        f"{optimized_summary.total_requests}"
    )

    print(
        f"Requests removed:        "
        f"{reduction}"
    )

    print(
        f"Reduction:               "
        f"{reduction_percent:.2f}%"
    )

    print()
    print(
        f"Controls before:         "
        f"{raw_summary.unique_controls_supported}"
    )

    print(
        f"Controls after:          "
        f"{optimized_summary.unique_controls_supported}"
    )

    print()
    print(
        f"Mappings before:         "
        f"{raw_summary.total_control_mappings}"
    )

    print(
        f"Mappings after:          "
        f"{optimized_summary.total_control_mappings}"
    )

    print()
    print(
        f"Reused before:           "
        f"{raw_summary.reused_requests}"
    )

    print(
        f"Reused after:            "
        f"{optimized_summary.reused_requests}"
    )

    print()
    print(
        "REMOVED / MERGED RAW TITLES"
    )
    print(
        "----------------------------------------"
    )

    for title in removed_titles:
        print(
            f"- {title}"
        )

    print()
    print(
        "NEW OPTIMIZED PACKAGE TITLES"
    )
    print(
        "----------------------------------------"
    )

    for title in added_titles:
        print(
            f"+ {title}"
        )

    print()
    print(
        "TOP 20 OPTIMIZED REQUESTS"
    )
    print(
        "----------------------------------------"
    )

    ranked = sorted(
        optimized_drl.requests,
        key=lambda request: (
            -request.reuse_count,
            request.requested_item.casefold(),
        ),
    )

    for request in ranked[:20]:
        print(
            f"{request.reuse_count:>3} controls  "
            f"{request.request_id:<8} "
            f"{request.requested_item}"
        )

    print(
        "========================================"
    )

    assert True