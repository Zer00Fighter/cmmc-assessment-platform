from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from src.compiler.content_parser import ParsedRequirement
from src.compiler.validator import ValidationReport


@dataclass(frozen=True)
class ExportPaths:
    controls_csv: Path
    objectives_csv: Path
    assessment_methods_csv: Path
    key_references_csv: Path
    compiler_report_json: Path


class CompilerExporter:
    """
    Export validated CMMC compiler output into production CSV and JSON files.

    The exporter does not perform validation itself. Call the validator first
    and pass the resulting ValidationReport to export_all().
    """

    SOURCE_DOCUMENT = "AssessmentGuideL2v2.pdf"
    SOURCE_VERSION = "2.13"

    def __init__(
        self,
        project_root: Path,
    ) -> None:
        self.project_root = project_root.resolve()

        self.controls_directory = (
            self.project_root
            / "data"
            / "controls"
        )

        self.mappings_directory = (
            self.project_root
            / "data"
            / "mappings"
        )

        self.compiler_directory = (
            self.project_root
            / "data"
            / "compiler"
        )

    def get_export_paths(self) -> ExportPaths:
        return ExportPaths(
            controls_csv=(
                self.controls_directory
                / "cmmc_level2_controls.csv"
            ),
            objectives_csv=(
                self.controls_directory
                / "cmmc_level2_objectives.csv"
            ),
            assessment_methods_csv=(
                self.mappings_directory
                / "assessment_methods.csv"
            ),
            key_references_csv=(
                self.mappings_directory
                / "key_references.csv"
            ),
            compiler_report_json=(
                self.compiler_directory
                / "compiler_report.json"
            ),
        )

    def export_all(
        self,
        requirements: Sequence[ParsedRequirement],
        validation_report: ValidationReport,
    ) -> ExportPaths:
        """
        Export all production data files.

        Raises:
            ValueError: If validation did not pass.
        """

        if not validation_report.passed:
            raise ValueError(
                "Cannot export compiler data because validation failed."
            )

        self._ensure_directories()

        paths = self.get_export_paths()

        self.export_controls(
            requirements=requirements,
            output_path=paths.controls_csv,
        )

        self.export_objectives(
            requirements=requirements,
            output_path=paths.objectives_csv,
        )

        self.export_assessment_methods(
            requirements=requirements,
            output_path=paths.assessment_methods_csv,
        )

        self.export_key_references(
            requirements=requirements,
            output_path=paths.key_references_csv,
        )

        self.export_compiler_report(
            requirements=requirements,
            validation_report=validation_report,
            output_path=paths.compiler_report_json,
        )

        return paths

    def export_controls(
        self,
        requirements: Sequence[ParsedRequirement],
        output_path: Path,
    ) -> None:
        fieldnames = [
            "domain_code",
            "requirement_id",
            "title",
            "statement",
            "source_page_start",
            "source_page_end",
            "source_document",
            "source_version",
        ]

        rows = [
            {
                "domain_code": requirement.domain_code,
                "requirement_id": requirement.requirement_id,
                "title": requirement.title,
                "statement": requirement.statement,
                "source_page_start": (
                    requirement.source_page_start
                ),
                "source_page_end": (
                    requirement.source_page_end
                ),
                "source_document": self.SOURCE_DOCUMENT,
                "source_version": self.SOURCE_VERSION,
            }
            for requirement in requirements
        ]

        self._write_csv(
            output_path=output_path,
            fieldnames=fieldnames,
            rows=rows,
        )

    def export_objectives(
        self,
        requirements: Sequence[ParsedRequirement],
        output_path: Path,
    ) -> None:
        fieldnames = [
            "requirement_id",
            "objective_id",
            "objective_text",
            "source_page_start",
            "source_page_end",
            "source_document",
            "source_version",
        ]

        rows: List[Dict[str, object]] = []

        for requirement in requirements:
            for objective in requirement.objectives:
                rows.append(
                    {
                        "requirement_id": (
                            requirement.requirement_id
                        ),
                        "objective_id": (
                            objective.objective_id
                        ),
                        "objective_text": (
                            objective.objective_text
                        ),
                        "source_page_start": (
                            requirement.source_page_start
                        ),
                        "source_page_end": (
                            requirement.source_page_end
                        ),
                        "source_document": (
                            self.SOURCE_DOCUMENT
                        ),
                        "source_version": (
                            self.SOURCE_VERSION
                        ),
                    }
                )

        self._write_csv(
            output_path=output_path,
            fieldnames=fieldnames,
            rows=rows,
        )

    def export_assessment_methods(
        self,
        requirements: Sequence[ParsedRequirement],
        output_path: Path,
    ) -> None:
        fieldnames = [
            "requirement_id",
            "method",
            "object_sequence",
            "assessment_object",
            "source_page_start",
            "source_page_end",
        ]

        rows: List[Dict[str, object]] = []

        for requirement in requirements:
            method_mapping = {
                "EXAMINE": requirement.examine_objects,
                "INTERVIEW": requirement.interview_objects,
                "TEST": requirement.test_objects,
            }

            for method_name, objects in method_mapping.items():
                for sequence, assessment_object in enumerate(
                    objects,
                    start=1,
                ):
                    rows.append(
                        {
                            "requirement_id": (
                                requirement.requirement_id
                            ),
                            "method": method_name,
                            "object_sequence": sequence,
                            "assessment_object": (
                                assessment_object
                            ),
                            "source_page_start": (
                                requirement.source_page_start
                            ),
                            "source_page_end": (
                                requirement.source_page_end
                            ),
                        }
                    )

        self._write_csv(
            output_path=output_path,
            fieldnames=fieldnames,
            rows=rows,
        )

    def export_key_references(
        self,
        requirements: Sequence[ParsedRequirement],
        output_path: Path,
    ) -> None:
        fieldnames = [
            "requirement_id",
            "reference_sequence",
            "reference_text",
            "source_page_start",
            "source_page_end",
        ]

        rows: List[Dict[str, object]] = []

        for requirement in requirements:
            for sequence, reference in enumerate(
                requirement.key_references,
                start=1,
            ):
                rows.append(
                    {
                        "requirement_id": (
                            requirement.requirement_id
                        ),
                        "reference_sequence": sequence,
                        "reference_text": reference,
                        "source_page_start": (
                            requirement.source_page_start
                        ),
                        "source_page_end": (
                            requirement.source_page_end
                        ),
                    }
                )

        self._write_csv(
            output_path=output_path,
            fieldnames=fieldnames,
            rows=rows,
        )

    def export_compiler_report(
        self,
        requirements: Sequence[ParsedRequirement],
        validation_report: ValidationReport,
        output_path: Path,
    ) -> None:
        objective_count = sum(
            len(requirement.objectives)
            for requirement in requirements
        )

        examine_object_count = sum(
            len(requirement.examine_objects)
            for requirement in requirements
        )

        interview_object_count = sum(
            len(requirement.interview_objects)
            for requirement in requirements
        )

        test_object_count = sum(
            len(requirement.test_objects)
            for requirement in requirements
        )

        reference_count = sum(
            len(requirement.key_references)
            for requirement in requirements
        )

        report = {
            "generated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "source_document": self.SOURCE_DOCUMENT,
            "source_version": self.SOURCE_VERSION,
            "validation_passed": (
                validation_report.passed
            ),
            "requirement_count": (
                validation_report.requirement_count
            ),
            "objective_count": objective_count,
            "domain_count": len(
                validation_report.domain_counts
            ),
            "domain_counts": (
                validation_report.domain_counts
            ),
            "assessment_method_object_counts": {
                "EXAMINE": examine_object_count,
                "INTERVIEW": interview_object_count,
                "TEST": test_object_count,
            },
            "key_reference_count": reference_count,
            "error_count": (
                validation_report.error_count
            ),
            "warning_count": (
                validation_report.warning_count
            ),
            "errors": [
                asdict(issue)
                for issue in validation_report.errors
            ],
            "warnings": [
                asdict(issue)
                for issue in validation_report.warnings
            ],
            "first_requirement": (
                requirements[0].requirement_id
                if requirements
                else None
            ),
            "last_requirement": (
                requirements[-1].requirement_id
                if requirements
                else None
            ),
            "export_files": {
                "controls": (
                    "data/controls/"
                    "cmmc_level2_controls.csv"
                ),
                "objectives": (
                    "data/controls/"
                    "cmmc_level2_objectives.csv"
                ),
                "assessment_methods": (
                    "data/mappings/"
                    "assessment_methods.csv"
                ),
                "key_references": (
                    "data/mappings/"
                    "key_references.csv"
                ),
            },
        }

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=2,
                ensure_ascii=False,
            )

            file.write("\n")

    def _ensure_directories(self) -> None:
        self.controls_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.mappings_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.compiler_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _write_csv(
        output_path: Path,
        fieldnames: Sequence[str],
        rows: Iterable[Dict[str, object]],
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(fieldnames),
                extrasaction="raise",
            )

            writer.writeheader()

            for row in rows:
                writer.writerow(row)