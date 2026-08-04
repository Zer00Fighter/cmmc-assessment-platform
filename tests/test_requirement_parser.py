from pathlib import Path

from src.compiler.pdf_extractor import PDFExtractor
from src.compiler.requirement_parser import RequirementParser


ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)


def load_blocks():
    extractor = PDFExtractor(PDF_PATH)
    pages = extractor.extract_pages()

    parser = RequirementParser()
    return parser.parse(pages)


def test_parser_detects_110_requirements() -> None:
    blocks = load_blocks()

    assert len(blocks) == 110


def test_first_requirement() -> None:
    blocks = load_blocks()
    first = blocks[0]

    assert first.requirement_id == "AC.L2-3.1.1"
    assert first.domain_code == "AC"


def test_last_requirement() -> None:
    blocks = load_blocks()
    last = blocks[-1]

    assert last.requirement_id == "SI.L2-3.14.7"
    assert last.domain_code == "SI"


def test_requirement_ids_are_unique() -> None:
    blocks = load_blocks()

    requirement_ids = [
        block.requirement_id
        for block in blocks
    ]

    assert len(requirement_ids) == len(set(requirement_ids))


def test_all_blocks_have_text() -> None:
    blocks = load_blocks()

    for block in blocks:
        assert block.raw_text.strip() != ""


def test_all_blocks_have_page_numbers() -> None:
    blocks = load_blocks()

    for block in blocks:
        assert block.source_page_start > 0
        assert block.source_page_end >= block.source_page_start


def test_first_requirement_contains_objectives() -> None:
    blocks = load_blocks()
    first = blocks[0]

    assert "ASSESSMENT OBJECTIVES" in first.raw_text.upper()
    assert "[a]" in first.raw_text
    assert "[f]" in first.raw_text