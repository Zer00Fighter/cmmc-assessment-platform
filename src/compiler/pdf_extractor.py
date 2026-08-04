from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


class PDFExtractor:
    def __init__(self, pdf_path: Path) -> None:
        self.pdf_path = pdf_path

    def validate_pdf(self) -> None:
        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"PDF file was not found: {self.pdf_path}"
            )

        if self.pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Expected a PDF file, received: {self.pdf_path}"
            )

    def extract_pages(self) -> List[ExtractedPage]:
        self.validate_pdf()

        reader = PdfReader(str(self.pdf_path))
        extracted_pages: List[ExtractedPage] = []

        for page_index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            extracted_pages.append(
                ExtractedPage(
                    page_number=page_index,
                    text=page_text.strip(),
                )
            )

        return extracted_pages

    def page_count(self) -> int:
        self.validate_pdf()

        reader = PdfReader(str(self.pdf_path))
        return len(reader.pages)