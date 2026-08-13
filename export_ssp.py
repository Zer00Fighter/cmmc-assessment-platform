"""Command-line entry point for Omni's Word SSP export."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ssp_export import (
    SSPExportMetadata,
    export_ssp,
    validate_ssp_readiness,
    write_readiness_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an Omni Security Plan to Word."
    )
    parser.add_argument(
        "--template", type=Path, required=True, help="Source SSP .docx template"
    )
    parser.add_argument(
        "--workbook", type=Path, required=True, help="Omni .xlsx workbook"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Destination .docx path"
    )
    parser.add_argument("--organization", default="", help="Organization name")
    parser.add_argument("--system", default="", help="System or assessment name")
    parser.add_argument("--system-owner", default="", help="System owner")
    parser.add_argument("--prepared-by", default="", help="Document preparer")
    parser.add_argument("--version", default="1.0", help="Document version")
    parser.add_argument("--export-date", default="", help="Export date (YYYY-MM-DD)")
    parser.add_argument(
        "--readiness-report",
        type=Path,
        help="Write the SSP readiness report to this text file",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Do not generate Word output when readiness blockers exist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate_ssp_readiness(args.workbook)
    report_path = args.readiness_report or args.output.with_suffix(".readiness.txt")
    write_readiness_report(report, report_path)
    print(report.to_text())
    print(f"Readiness report: {report_path.resolve()}")
    if args.require_ready and not report.ready:
        raise SystemExit(
            f"Completed SSP generation blocked by {len(report.blockers)} "
            "readiness issue(s)."
        )
    result = export_ssp(
        args.template,
        args.workbook,
        args.output,
        SSPExportMetadata(
            organization_name=args.organization,
            system_name=args.system,
            system_owner=args.system_owner,
            prepared_by=args.prepared_by,
            version=args.version,
            export_date=args.export_date,
        ),
    )
    print(f"Created Word SSP: {result}")


if __name__ == "__main__":
    main()
