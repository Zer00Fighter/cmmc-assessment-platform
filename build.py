from pathlib import Path

from src.workbook import WorkbookBuilder


ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("Building Omni CMMC Level 2 assessment workbook v1.0...")

    builder = WorkbookBuilder(
        project_root=ROOT,
    )

    output_path = builder.build()

    print("Workbook generated successfully:")
    print(output_path)


if __name__ == "__main__":
    main()
