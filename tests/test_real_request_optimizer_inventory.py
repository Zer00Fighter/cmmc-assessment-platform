from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, List

import pytest

from src.evidence_requests.assessment_procedure_loader import (
    AssessmentProcedureDataset,
    AssessmentProcedureLoader,
)
from src.evidence_requests.catalog_compiler import (
    CatalogCompiler,
)
from src.evidence_requests.drl_model import (
    DocumentationRequest,
    DocumentationRequestCollection,
    DocumentationRequestType,
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
def optimized_drl(
    dataset: AssessmentProcedureDataset,
) -> DocumentationRequestCollection:
    knowledge = CatalogCompiler().compile(
        dataset.rows
    )

    raw_drl = RequestGenerator().generate(
        knowledge,
        framework_id="CMMC_L2",
        engagement_name=(
            "Real SP 800-171A DRL Discovery"
        ),
        organization_name=(
            "Integration Test Organization"
        ),
    )

    return RequestOptimizer().optimize(
        raw_drl
    )


def _rank_requests(
    requests: List[
        DocumentationRequest
    ],
) -> List[
    DocumentationRequest
]:
    return sorted(
        requests,
        key=lambda request: (
            -request.reuse_count,
            request.requested_item.casefold(),
        ),
    )


def test_print_optimized_request_title_inventory(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    grouped: DefaultDict[
        DocumentationRequestType,
        List[DocumentationRequest],
    ] = defaultdict(list)

    for request in optimized_drl.requests:
        grouped[
            request.evidence_type
        ].append(
            request
        )

    print()
    print(
        "============================================================"
    )
    print(
        "REAL SP 800-171A OPTIMIZED DRL TITLE INVENTORY"
    )
    print(
        "============================================================"
    )

    print(
        f"Optimized requests: "
        f"{optimized_drl.count}"
    )

    print(
        f"Unique controls:    "
        f"{optimized_drl.summary.unique_controls_supported}"
    )

    print(
        f"Control mappings:   "
        f"{optimized_drl.summary.total_control_mappings}"
    )

    print()

    for evidence_type in sorted(
        grouped,
        key=lambda item:
            item.value.casefold(),
    ):
        requests = _rank_requests(
            grouped[evidence_type]
        )

        print(
            "------------------------------------------------------------"
        )

        print(
            f"{evidence_type.value.upper()} "
            f"({len(requests)} requests)"
        )

        print(
            "------------------------------------------------------------"
        )

        for request in requests:
            families = ", ".join(
                request.control_families
            )

            print(
                f"{request.reuse_count:>3} controls | "
                f"{request.request_id:<8} | "
                f"{request.requested_item}"
                + (
                    f" | families: {families}"
                    if families
                    else ""
                )
            )

        print()

    assert optimized_drl.count > 0


def test_print_top_merge_candidates(
    optimized_drl: DocumentationRequestCollection,
) -> None:
    ranked = _rank_requests(
        list(
            optimized_drl.requests
        )
    )

    candidates = [
        request
        for request in ranked
        if request.reuse_count >= 2
    ]

    print()
    print(
        "============================================================"
    )
    print(
        "TOP REMAINING DRL MERGE CANDIDATES"
    )
    print(
        "============================================================"
    )

    for request in candidates[:100]:
        print(
            f"{request.reuse_count:>3} controls | "
            f"{request.evidence_type.value:<24} | "
            f"{request.requested_item}"
        )

    print(
        "============================================================"
    )

    assert candidates