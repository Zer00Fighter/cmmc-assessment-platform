from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

import pytest

from src.compiler.content_parser import (
    ContentParser,
    ParsedRequirement,
)
from src.compiler.exporter import CompilerExporter
from src.compiler.normalizer import TextNormalizer
from src.compiler.pdf_extractor import PDFExtractor
from src.compiler.requirement_parser import RequirementParser
from src.compiler.validator import (
    RequirementValidator,
    ValidationReport,
)


ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)


@lru_cache(maxsize=1)
def load_normalized_requirements() -> (
    tuple[ParsedRequirement, ...]
):
    """
    Parse and normalize the Assessment Guide once for this test session.
    """

    extractor = PDFExtractor(PDF_PATH)
    pages = extractor.extract_pages()

    requirement_parser = RequirementParser()
    blocks = requirement_parser.parse(pages)

    content_parser = ContentParser()
    parsed_requirements = content_parser.parse_many(
        blocks
    )

    normalizer = TextNormalizer()
    normalized_requirements = normalizer.normalize_many(
        parsed_requirements
    )

    return tuple(normalized_requirements)


@lru_cache(maxsize=1)
def load_validation_report() -> ValidationReport:
    validator = RequirementValidator()

    return validator.validate(
        load_normalized_requirements()
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def test_exporter_creates_all_files(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    requirements = load_normalized_requirements()
    validation_report = load_validation_report()

    paths = exporter.export_all(
        requirements=requirements,
        validation_report=validation_report,
    )

    assert paths.controls_csv.exists()
    assert paths.objectives_csv.exists()
    assert paths.assessment_methods_csv.exists()
    assert paths.key_references_csv.exists()
    assert paths.compiler_report_json.exists()


def test_exported_controls_contains_110_rows(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(paths.controls_csv)

    assert len(rows) == 110

    assert rows[0]["requirement_id"] == (
        "AC.L2-3.1.1"
    )

    assert rows[-1]["requirement_id"] == (
        "SI.L2-3.14.7"
    )


def test_exported_controls_has_expected_columns(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(paths.controls_csv)

    assert rows

    assert list(rows[0].keys()) == [
        "domain_code",
        "requirement_id",
        "title",
        "statement",
        "source_page_start",
        "source_page_end",
        "source_document",
        "source_version",
    ]


def test_exported_first_control_is_correct(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(paths.controls_csv)
    first = rows[0]

    assert first["domain_code"] == "AC"
    assert first["requirement_id"] == (
        "AC.L2-3.1.1"
    )

    assert (
        "AUTHORIZED ACCESS CONTROL"
        in first["title"].upper()
    )

    assert first["statement"].startswith(
        "Limit system access to authorized users"
    )

    assert first["source_document"] == (
        "AssessmentGuideL2v2.pdf"
    )

    assert first["source_version"] == "2.13"


def test_exported_objectives_are_present(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(paths.objectives_csv)

    assert len(rows) > 110

    first_requirement_rows = [
        row
        for row in rows
        if row["requirement_id"]
        == "AC.L2-3.1.1"
    ]

    assert len(first_requirement_rows) == 6

    assert [
        row["objective_id"]
        for row in first_requirement_rows
    ] == [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
    ]


def test_exported_assessment_methods_are_present(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(
        paths.assessment_methods_csv
    )

    assert rows

    methods = {
        row["method"]
        for row in rows
    }

    assert "EXAMINE" in methods
    assert "INTERVIEW" in methods
    assert "TEST" in methods

    first_requirement_methods = {
        row["method"]
        for row in rows
        if row["requirement_id"]
        == "AC.L2-3.1.1"
    }

    assert first_requirement_methods == {
        "EXAMINE",
        "INTERVIEW",
        "TEST",
    }


def test_exported_key_references_are_present(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    rows = read_csv_rows(
        paths.key_references_csv
    )

    assert rows

    first_requirement_references = [
        row["reference_text"]
        for row in rows
        if row["requirement_id"]
        == "AC.L2-3.1.1"
    ]

    assert first_requirement_references

    assert any(
        "NIST SP 800-171" in reference
        for reference in first_requirement_references
    )


def test_compiler_report_is_valid_json(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    paths = exporter.export_all(
        requirements=load_normalized_requirements(),
        validation_report=load_validation_report(),
    )

    with paths.compiler_report_json.open(
        "r",
        encoding="utf-8",
    ) as file:
        report = json.load(file)

    assert report["validation_passed"] is True
    assert report["requirement_count"] == 110
    assert report["domain_count"] == 14
    assert report["objective_count"] > 110

    assert report["first_requirement"] == (
        "AC.L2-3.1.1"
    )

    assert report["last_requirement"] == (
        "SI.L2-3.14.7"
    )

    assert report["source_version"] == "2.13"


def test_exporter_uses_expected_directories(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)
    paths = exporter.get_export_paths()

    assert paths.controls_csv == (
        tmp_path
        / "data"
        / "controls"
        / "cmmc_level2_controls.csv"
    )

    assert paths.objectives_csv == (
        tmp_path
        / "data"
        / "controls"
        / "cmmc_level2_objectives.csv"
    )

    assert paths.assessment_methods_csv == (
        tmp_path
        / "data"
        / "mappings"
        / "assessment_methods.csv"
    )

    assert paths.key_references_csv == (
        tmp_path
        / "data"
        / "mappings"
        / "key_references.csv"
    )

    assert paths.compiler_report_json == (
        tmp_path
        / "data"
        / "compiler"
        / "compiler_report.json"
    )


def test_exporter_rejects_failed_validation(
    tmp_path: Path,
) -> None:
    exporter = CompilerExporter(tmp_path)

    failed_report = ValidationReport(
        requirement_count=0,
        domain_counts={},
    )

    failed_report.errors.append(
        load_validation_report().errors[0]
        if load_validation_report().errors
        else _make_test_validation_issue()
    )

    with pytest.raises(
        ValueError,
        match="validation failed",
    ):
        exporter.export_all(
            requirements=[],
            validation_report=failed_report,
        )


def _make_test_validation_issue():
    from src.compiler.validator import (
        ValidationIssue,
    )

    return ValidationIssue(
        severity="ERROR",
        code="TEST_ERROR",
        message="Intentional exporter test error.",
    )