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

#
# ============================================================
# REAL SOURCE WORKBOOK
# ============================================================
#
# CHANGE THIS PATH ONLY if your real workbook has a
# different filename or location.
#

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_WORKBOOK = (
    PROJECT_ROOT
    / "data"
    / "sp800-171a-assessment-procedures.xlsx"
)

#
# ============================================================
# KNOWN SOURCE-DATA FALLBACKS
# ============================================================
#
# The source workbook has a genuinely blank Security
# Requirement cell for 3.13.12.
#
# Keep source defects here rather than hard-coding them
# into AssessmentProcedureLoader.
#

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


#
# ============================================================
# FIXTURES
# ============================================================
#

@pytest.fixture(scope="module")
def real_workbook() -> Path:
    """
    Return the authoritative assessment-procedure workbook.

    We intentionally fail rather than skip when the workbook
    is missing because this is an integration test intended
    to validate the real framework source.
    """

    assert SOURCE_WORKBOOK.exists(), (
        "\n\nReal assessment procedure workbook was not found:\n"
        f"{SOURCE_WORKBOOK}\n\n"
        "Update SOURCE_WORKBOOK at the top of "
        "tests/test_real_assessment_procedure_loader.py "
        "to point to the actual workbook.\n"
    )

    assert SOURCE_WORKBOOK.is_file()

    return SOURCE_WORKBOOK


@pytest.fixture(scope="module")
def loader() -> AssessmentProcedureLoader:
    return AssessmentProcedureLoader(
        framework_id="CMMC_L2",
        framework_name="CMMC Level 2",
        framework_version="2.0",
        source_document="NIST SP 800-171A",
        source_revision="Rev. 2",
        requirement_text_provider=(
            requirement_text_provider
        ),
    )


@pytest.fixture(scope="module")
def dataset(
    loader: AssessmentProcedureLoader,
    real_workbook: Path,
) -> AssessmentProcedureDataset:
    return loader.load(
        real_workbook
    )


#
# ============================================================
# BASIC LOAD VALIDATION
# ============================================================
#

def test_real_workbook_loads(
    dataset: AssessmentProcedureDataset,
) -> None:
    assert isinstance(
        dataset,
        AssessmentProcedureDataset,
    )

    assert dataset.framework_id == "CMMC_L2"

    assert dataset.source_sheet == "SP800-171A"

    assert dataset.source_file


def test_real_dataset_is_not_empty(
    dataset: AssessmentProcedureDataset,
) -> None:
    assert dataset.row_count > 0

    assert dataset.requirement_count > 0

    assert dataset.objective_count > 0


#
# ============================================================
# EXPECTED FRAMEWORK SCALE
# ============================================================
#
# Initially use defensible minimum counts.
#
# Once we see the exact output from the authoritative
# workbook, we can convert these into exact regression
# assertions.
#

def test_real_dataset_contains_full_requirement_set(
    dataset: AssessmentProcedureDataset,
) -> None:
    assert dataset.requirement_count >= 100


def test_real_dataset_contains_assessment_objectives(
    dataset: AssessmentProcedureDataset,
) -> None:
    assert dataset.objective_count >= 297


def test_real_dataset_has_requirement_and_objective_rows(
    dataset: AssessmentProcedureDataset,
) -> None:
    assert (
        dataset.row_count
        >
        dataset.requirement_count
    )

    assert (
        dataset.row_count
        >
        dataset.objective_count
    )


#
# ============================================================
# CANONICAL CONTROL IDS
# ============================================================
#

def test_real_dataset_uses_canonical_cmmc_ids(
    dataset: AssessmentProcedureDataset,
) -> None:
    requirement_ids = set(
        dataset.requirement_ids
    )

    assert (
        "AC.L2-3.1.1"
        in requirement_ids
    )

    assert (
        "IA.L2-3.5.3"
        in requirement_ids
    )

    assert (
        "SC.L2-3.13.12"
        in requirement_ids
    )


def test_real_requirement_ids_include_family(
    dataset: AssessmentProcedureDataset,
) -> None:
    for requirement_id in dataset.requirement_ids:
        assert ".L2-" in requirement_id

        family, remainder = (
            requirement_id.split(
                ".L2-",
                1,
            )
        )

        assert family
        assert remainder


def test_real_requirement_ids_do_not_use_raw_nist_ids(
    dataset: AssessmentProcedureDataset,
) -> None:
    requirement_ids = set(
        dataset.requirement_ids
    )

    assert "3.1.1" not in requirement_ids

    assert "3.5.3" not in requirement_ids

    assert "3.13.12" not in requirement_ids


#
# ============================================================
# AC.L2-3.1.1 VALIDATION
# ============================================================
#

def test_real_ac_3_1_1_exists(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    assert rows


def test_real_ac_3_1_1_has_base_requirement(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    base_rows = [
        row
        for row in rows
        if not row.objective_id
    ]

    assert len(base_rows) == 1

    base = base_rows[0]

    assert base.requirement_id == (
        "AC.L2-3.1.1"
    )

    assert base.requirement_text


def test_real_ac_3_1_1_has_objectives(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    objective_rows = [
        row
        for row in rows
        if row.objective_id
    ]

    assert objective_rows

    objective_ids = {
        row.objective_id
        for row in objective_rows
    }

    assert "a" in objective_ids

    assert "b" in objective_ids


#
# ============================================================
# ASSESSMENT METHOD INHERITANCE
# ============================================================
#

def test_real_objectives_inherit_examine(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    objective_rows = [
        row
        for row in rows
        if row.objective_id
    ]

    assert objective_rows

    for row in objective_rows:
        assert row.examine


def test_real_objectives_inherit_interview(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    objective_rows = [
        row
        for row in rows
        if row.objective_id
    ]

    assert objective_rows

    for row in objective_rows:
        assert row.interview


def test_real_objectives_inherit_test(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "AC.L2-3.1.1"
    )

    objective_rows = [
        row
        for row in rows
        if row.objective_id
    ]

    assert objective_rows

    for row in objective_rows:
        assert row.test


#
# ============================================================
# KNOWN 3.12.4 DOTTED OBJECTIVE FORMAT
# ============================================================
#
# The real workbook contains:
#
#     3.12.4.[h]
#
# The loader must normalize this to:
#
#     CA.L2-3.12.4
#     objective h
#

def test_real_dotted_objective_identifier_loads(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "CA.L2-3.12.4"
    )

    assert rows

    objective_ids = {
        row.objective_id
        for row in rows
        if row.objective_id
    }

    assert "h" in objective_ids


#
# ============================================================
# KNOWN BLANK 3.13.12 REQUIREMENT
# ============================================================
#

def test_real_sc_3_13_12_uses_fallback_text(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "SC.L2-3.13.12"
    )

    assert rows

    base = next(
        row
        for row in rows
        if not row.objective_id
    )

    assert base.requirement_text

    assert (
        "collaborative computing"
        in base.requirement_text.casefold()
    )


def test_real_sc_3_13_12_objectives_receive_requirement_text(
    dataset: AssessmentProcedureDataset,
) -> None:
    rows = dataset.for_requirement(
        "SC.L2-3.13.12"
    )

    objective_rows = [
        row
        for row in rows
        if row.objective_id
    ]

    assert objective_rows

    for row in objective_rows:
        assert row.requirement_text

        assert (
            "collaborative computing"
            in row.requirement_text.casefold()
        )


#
# ============================================================
# NO ORPHAN OBJECTIVES
# ============================================================
#

def test_real_dataset_has_no_orphan_objectives(
    dataset: AssessmentProcedureDataset,
) -> None:
    base_requirements = {
        row.requirement_id.casefold()
        for row in dataset.rows
        if not row.objective_id
    }

    assert base_requirements

    for row in dataset.rows:
        if not row.objective_id:
            continue

        assert (
            row.requirement_id.casefold()
            in base_requirements
        ), (
            "Orphan objective found: "
            f"{row.requirement_id}"
            f"[{row.objective_id}]"
        )


#
# ============================================================
# ALL REQUIREMENTS HAVE TEXT
# ============================================================
#

def test_real_dataset_all_requirements_have_text(
    dataset: AssessmentProcedureDataset,
) -> None:
    blank = [
        row.requirement_id
        for row in dataset.rows
        if (
            not row.objective_id
            and not row.requirement_text
        )
    ]

    assert blank == []


def test_real_dataset_all_objectives_have_text(
    dataset: AssessmentProcedureDataset,
) -> None:
    blank = [
        (
            row.requirement_id,
            row.objective_id,
        )
        for row in dataset.rows
        if (
            row.objective_id
            and not row.objective_text
        )
    ]

    assert blank == []


#
# ============================================================
# SOURCE PROVENANCE
# ============================================================
#

def test_real_dataset_preserves_source_locations(
    dataset: AssessmentProcedureDataset,
) -> None:
    for row in dataset.rows:
        assert row.source_location

        assert (
            "SP800-171A!Row "
            in row.source_location
        )


#
# ============================================================
# REAL KNOWLEDGE COMPILATION
# ============================================================
#
# This is deliberately a small integration check.
#
# Detailed CatalogCompiler behavior is already covered by
# tests/test_catalog_compiler.py.
#

@pytest.fixture(scope="module")
def compiled_knowledge(
    dataset: AssessmentProcedureDataset,
):
    return CatalogCompiler().compile(
        dataset.rows
    )


def test_real_dataset_compiles(
    compiled_knowledge,
) -> None:
    assert compiled_knowledge.requirements

    assert compiled_knowledge.objectives

    assert compiled_knowledge.evidence

    assert compiled_knowledge.interviews

    assert compiled_knowledge.tests


def test_real_compiler_requirement_count_matches_loader(
    dataset: AssessmentProcedureDataset,
    compiled_knowledge,
) -> None:
    assert (
        len(
            compiled_knowledge.requirements
        )
        == dataset.requirement_count
    )


def test_real_compiler_objective_count_matches_loader(
    dataset: AssessmentProcedureDataset,
    compiled_knowledge,
) -> None:
    assert (
        len(
            compiled_knowledge.objectives
        )
        == dataset.objective_count
    )


def test_real_compiler_produces_evidence(
    compiled_knowledge,
) -> None:
    assert (
        compiled_knowledge.statistics
        .evidence_count
        > 0
    )


def test_real_compiler_produces_interviews(
    compiled_knowledge,
) -> None:
    assert (
        compiled_knowledge.statistics
        .interview_count
        > 0
    )


def test_real_compiler_produces_tests(
    compiled_knowledge,
) -> None:
    assert (
        compiled_knowledge.statistics
        .test_count
        > 0
    )


#
# ============================================================
# DIAGNOSTIC OUTPUT
# ============================================================
#
# Run pytest with:
#
#     -s
#
# to display these numbers.
#

def test_print_real_framework_statistics(
    dataset: AssessmentProcedureDataset,
    compiled_knowledge,
) -> None:
    stats = (
        compiled_knowledge.statistics
    )

    print()
    print(
        "========================================"
    )
    print(
        "REAL NIST SP 800-171A COMPILATION"
    )
    print(
        "========================================"
    )

    print(
        f"Loader rows:          "
        f"{dataset.row_count}"
    )

    print(
        f"Requirements:         "
        f"{dataset.requirement_count}"
    )

    print(
        f"Objectives:           "
        f"{dataset.objective_count}"
    )

    print(
        f"Unique evidence:      "
        f"{stats.evidence_count}"
    )

    print(
        f"Reusable evidence:    "
        f"{stats.reusable_evidence_count}"
    )

    print(
        f"Interview subjects:   "
        f"{stats.interview_count}"
    )

    print(
        f"Test targets:         "
        f"{stats.test_count}"
    )

    print()
    print(
        "TOP 20 REUSED EVIDENCE OBJECTS"
    )
    print(
        "----------------------------------------"
    )

    reused = sorted(
        compiled_knowledge.evidence,
        key=lambda item:
        item.requirement_count,
        reverse=True,
    )

    for item in reused[:20]:
        print(
            f"{item.requirement_count:>3} controls  "
            f"{item.title}"
        )

    print(
        "========================================"
    )

    assert True