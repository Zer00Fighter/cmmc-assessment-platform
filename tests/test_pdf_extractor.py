from pathlib import Path

from src.compiler.pdf_extractor import PDFExtractor


ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)


def test_pdf_exists() -> None:
    assert PDF_PATH.exists()


def test_pdf_page_count() -> None:
    extractor = PDFExtractor(PDF_PATH)

    assert extractor.page_count() == 276


def test_pdf_extracts_text() -> None:
    extractor = PDFExtractor(PDF_PATH)
    pages = extractor.extract_pages()

    assert len(pages) == extractor.page_count()
    assert len(pages) > 250
    assert pages[0].text.strip() != ""


def test_guide_contains_first_requirement() -> None:
    extractor = PDFExtractor(PDF_PATH)
    pages = extractor.extract_pages()

    all_text = "\n".join(
        page.text
        for page in pages
    )

    assert "AC.L2-3.1.1" in all_text