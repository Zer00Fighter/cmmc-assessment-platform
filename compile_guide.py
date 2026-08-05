from pathlib import Path

from src.compiler import (
    CompilerExporter,
    ContentParser,
    PDFExtractor,
    RequirementParser,
    RequirementValidator,
    TextNormalizer,
)


ROOT = Path(__file__).resolve().parent

PDF_PATH = (
    ROOT
    / "docs"
    / "source"
    / "AssessmentGuideL2v2.pdf"
)


def main() -> None:
    print("=" * 70)
    print("CMMC LEVEL 2 DATA COMPILER")
    print("=" * 70)

    print("\n1. Reading Assessment Guide PDF...")
    print(f"   Source: {PDF_PATH}")

    extractor = PDFExtractor(PDF_PATH)

    page_count = extractor.page_count()
    print(f"   Physical PDF pages: {page_count}")

    pages = extractor.extract_pages()
    print(f"   Extracted pages: {len(pages)}")

    print("\n2. Detecting requirement sections...")

    requirement_parser = RequirementParser()
    requirement_blocks = requirement_parser.parse(pages)

    print(
        "   Requirement sections detected: "
        f"{len(requirement_blocks)}"
    )

    if requirement_blocks:
        print(
            "   First requirement: "
            f"{requirement_blocks[0].requirement_id}"
        )
        print(
            "   Last requirement: "
            f"{requirement_blocks[-1].requirement_id}"
        )

    print("\n3. Parsing requirement content...")

    content_parser = ContentParser()
    parsed_requirements = content_parser.parse_many(
        requirement_blocks
    )

    print(
        "   Requirements parsed: "
        f"{len(parsed_requirements)}"
    )

    objective_count = sum(
        len(requirement.objectives)
        for requirement in parsed_requirements
    )

    print(
        "   Assessment objectives parsed: "
        f"{objective_count}"
    )

    print("\n4. Normalizing extracted content...")

    normalizer = TextNormalizer()

    normalized_requirements = normalizer.normalize_many(
        parsed_requirements
    )

    print(
        "   Requirements normalized: "
        f"{len(normalized_requirements)}"
    )

    print("\n5. Validating compiled data...")

    validator = RequirementValidator()

    validation_report = validator.validate_or_raise(
        normalized_requirements
    )

    print("   Validation passed.")
    print(
        "   Requirement count: "
        f"{validation_report.requirement_count}"
    )
    print(
        "   Domain count: "
        f"{len(validation_report.domain_counts)}"
    )
    print(
        "   Errors: "
        f"{validation_report.error_count}"
    )
    print(
        "   Warnings: "
        f"{validation_report.warning_count}"
    )

    if validation_report.warnings:
        print("\n   Validation warnings:")

        for warning in validation_report.warnings:
            requirement_label = (
                f" [{warning.requirement_id}]"
                if warning.requirement_id
                else ""
            )

            print(
                f"   - {warning.code}"
                f"{requirement_label}: "
                f"{warning.message}"
            )

    print("\n6. Exporting production data files...")

    exporter = CompilerExporter(
        project_root=ROOT,
    )

    export_paths = exporter.export_all(
        requirements=normalized_requirements,
        validation_report=validation_report,
    )

    print("\n   Exported files:")
    print(f"   Controls: {export_paths.controls_csv}")
    print(f"   Objectives: {export_paths.objectives_csv}")
    print(
        "   Assessment methods: "
        f"{export_paths.assessment_methods_csv}"
    )
    print(
        "   Key references: "
        f"{export_paths.key_references_csv}"
    )
    print(
        "   Compiler report: "
        f"{export_paths.compiler_report_json}"
    )

    print("\n" + "=" * 70)
    print("CMMC DATA COMPILATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()