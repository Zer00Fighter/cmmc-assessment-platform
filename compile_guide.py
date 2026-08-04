from pathlib import Path

from src.compiler.pdf_extractor import PDFExtractor
from src.compiler.requirement_parser import RequirementParser


ROOT = Path(__file__).resolve().parent

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)

OUTPUT_DIRECTORY = ROOT / "data" / "compiler"

EXTRACTED_TEXT_PATH = (
    OUTPUT_DIRECTORY
    / "assessment_guide_extracted.txt"
)


def main() -> None:
    print("Starting CMMC Assessment Guide extraction...")
    print(f"Source PDF: {PDF_PATH}")

    extractor = PDFExtractor(PDF_PATH)

    page_count = extractor.page_count()
    print(f"PDF page count: {page_count}")

    pages = extractor.extract_pages()
    print(f"Extracted pages: {len(pages)}")

    parser = RequirementParser()
    requirement_blocks = parser.parse(pages)

    print(
        "Detected requirement sections: "
        f"{len(requirement_blocks)}"
    )

    if requirement_blocks:
        first_requirement = requirement_blocks[0]
        last_requirement = requirement_blocks[-1]

        print(
            "First requirement: "
            f"{first_requirement.requirement_id} - "
            f"{first_requirement.title}"
        )

        print(
            "Last requirement: "
            f"{last_requirement.requirement_id} - "
            f"{last_requirement.title}"
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with EXTRACTED_TEXT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for page in pages:
            output_file.write(
                f"\n{'=' * 80}\n"
            )
            output_file.write(
                f"PAGE {page.page_number}\n"
            )
            output_file.write(
                f"{'=' * 80}\n\n"
            )
            output_file.write(page.text)
            output_file.write("\n")

    print(
        "Extracted text saved to: "
        f"{EXTRACTED_TEXT_PATH}"
    )

    if pages:
        preview = pages[0].text[:500]

        print("\nFirst-page preview:")
        print("-" * 60)
        print(preview)
        print("-" * 60)

    print("PDF extraction and requirement parsing completed successfully.")


if __name__ == "__main__":
    main()