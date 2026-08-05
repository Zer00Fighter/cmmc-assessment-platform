from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest

from src.compiler.content_parser import (
    ContentParser,
    ParsedObjective,
    ParsedRequirement,
)
from src.compiler.normalizer import TextNormalizer
from src.compiler.pdf_extractor import PDFExtractor
from src.compiler.requirement_parser import RequirementParser
from src.compiler.validator import (
    EXPECTED_DOMAIN_COUNTS,
    RequirementValidator,
    ValidationError,
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


def test_validator_accepts_compiled_guide() -> None:
    validator = RequirementValidator()
    requirements = load_normalized_requirements()

    report = validator.validate(requirements)

    assert report.passed
    assert report.error_count == 0
    assert report.requirement_count == 110


def test_validator_confirms_domain_counts() -> None:
    validator = RequirementValidator()
    requirements = load_normalized_requirements()

    report = validator.validate(requirements)

    assert report.domain_counts == EXPECTED_DOMAIN_COUNTS


def test_validator_rejects_missing_requirement() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )
    requirements.pop()

    report = validator.validate(requirements)

    assert not report.passed

    error_codes = {
        issue.code
        for issue in report.errors
    }

    assert "REQUIREMENT_COUNT" in error_codes
    assert "DOMAIN_COUNT" in error_codes
    assert "LAST_REQUIREMENT" in error_codes


def test_validator_rejects_duplicate_requirement() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )
    requirements.append(requirements[0])

    report = validator.validate(requirements)

    error_codes = {
        issue.code
        for issue in report.errors
    }

    assert "DUPLICATE_REQUIREMENT_ID" in error_codes


def test_validator_rejects_empty_statement() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )

    requirements[0] = replace(
        requirements[0],
        statement="",
    )

    report = validator.validate(requirements)

    assert any(
        issue.code == "EMPTY_STATEMENT"
        and issue.requirement_id
        == "AC.L2-3.1.1"
        for issue in report.errors
    )


def test_validator_rejects_missing_objectives() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )

    requirements[0] = replace(
        requirements[0],
        objectives=[],
    )

    report = validator.validate(requirements)

    assert any(
        issue.code == "MISSING_OBJECTIVES"
        for issue in report.errors
    )


def test_validator_rejects_duplicate_objective() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )

    first_requirement = requirements[0]
    first_objective = first_requirement.objectives[0]

    duplicate_objective = ParsedObjective(
        requirement_id=(
            first_objective.requirement_id
        ),
        objective_id=first_objective.objective_id,
        objective_text=first_objective.objective_text,
    )

    requirements[0] = replace(
        first_requirement,
        objectives=[
            *first_requirement.objectives,
            duplicate_objective,
        ],
    )

    report = validator.validate(requirements)

    assert any(
        issue.code == "DUPLICATE_OBJECTIVE_ID"
        for issue in report.errors
    )


def test_validator_rejects_invalid_page_range() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )

    requirements[0] = replace(
        requirements[0],
        source_page_start=30,
        source_page_end=20,
    )

    report = validator.validate(requirements)

    assert any(
        issue.code == "INVALID_PAGE_RANGE"
        for issue in report.errors
    )


def test_validate_or_raise_raises_validation_error() -> None:
    validator = RequirementValidator()

    requirements = list(
        load_normalized_requirements()
    )
    requirements.pop()

    with pytest.raises(ValidationError):
        validator.validate_or_raise(requirements)


def test_validation_report_raise_for_errors_passes() -> None:
    validator = RequirementValidator()
    requirements = load_normalized_requirements()

    report = validator.validate(requirements)

    report.raise_for_errors()