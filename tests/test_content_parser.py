from functools import lru_cache
from pathlib import Path

from src.compiler.content_parser import (
    ContentParser,
    ParsedRequirement,
)
from src.compiler.pdf_extractor import PDFExtractor
from src.compiler.requirement_parser import RequirementParser


ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)


@lru_cache(maxsize=1)
def load_parsed_requirements() -> tuple[ParsedRequirement, ...]:
    extractor = PDFExtractor(PDF_PATH)
    pages = extractor.extract_pages()

    requirement_parser = RequirementParser()
    blocks = requirement_parser.parse(pages)

    content_parser = ContentParser()
    return tuple(content_parser.parse_many(blocks))


def get_requirement(
    requirement_id: str,
) -> ParsedRequirement:
    requirements = load_parsed_requirements()

    for requirement in requirements:
        if requirement.requirement_id == requirement_id:
            return requirement

    raise AssertionError(
        f"Requirement was not parsed: {requirement_id}"
    )


def test_content_parser_parses_110_requirements() -> None:
    requirements = load_parsed_requirements()

    assert len(requirements) == 110


def test_ac_3_1_1_statement() -> None:
    requirement = get_requirement("AC.L2-3.1.1")

    assert requirement.statement
    assert requirement.statement.startswith(
        "Limit system access to authorized users"
    )


def test_ac_3_1_1_has_six_objectives() -> None:
    requirement = get_requirement("AC.L2-3.1.1")

    assert len(requirement.objectives) == 6

    objective_ids = [
        objective.objective_id
        for objective in requirement.objectives
    ]

    assert objective_ids == [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
    ]


def test_ac_3_1_1_first_objective() -> None:
    requirement = get_requirement("AC.L2-3.1.1")
    first_objective = requirement.objectives[0]

    assert first_objective.objective_id == "a"
    assert (
        "authorized users are identified"
        in first_objective.objective_text.lower()
    )


def test_ac_3_1_2_has_two_objectives() -> None:
    requirement = get_requirement("AC.L2-3.1.2")

    assert len(requirement.objectives) == 2

    objective_ids = [
        objective.objective_id
        for objective in requirement.objectives
    ]

    assert objective_ids == ["a", "b"]


def test_ac_3_1_1_has_assessment_methods() -> None:
    requirement = get_requirement("AC.L2-3.1.1")

    assert requirement.examine_objects
    assert requirement.interview_objects
    assert requirement.test_objects


def test_ac_3_1_1_has_key_references() -> None:
    requirement = get_requirement("AC.L2-3.1.1")

    assert requirement.key_references

    assert any(
        "NIST SP 800-171" in reference
        for reference in requirement.key_references
    )


def test_source_page_traceability_is_preserved() -> None:
    requirement = get_requirement("AC.L2-3.1.1")

    assert requirement.source_page_start > 0
    assert (
        requirement.source_page_end
        >= requirement.source_page_start
    )


def test_all_requirements_have_statements() -> None:
    requirements = load_parsed_requirements()

    missing_statements = [
        requirement.requirement_id
        for requirement in requirements
        if not requirement.statement.strip()
    ]

    assert missing_statements == []


def test_all_requirements_have_objectives() -> None:
    requirements = load_parsed_requirements()

    missing_objectives = [
        requirement.requirement_id
        for requirement in requirements
        if not requirement.objectives
    ]

    assert missing_objectives == []