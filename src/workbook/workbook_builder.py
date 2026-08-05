from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from src.workbook.workbook_styles import WorkbookStyles
from src.workbook.worksheet_factory import WorksheetFactory


class WorkbookBuilder:
    """Build the CMMC Level 2 assessment workbook."""

    SHEET_ORDER = [
        "Cover",
        "Dashboard",
        "Assessment",
        "Domain Summary",
        "Evidence",
        "POA&M",
        "SSP Crosswalk",
        "Assessment History",
        "Executive Report",
        "Settings",
        "_Lists",
    ]

    FIRST_ASSESSMENT_ROW = 6
    EXPECTED_CONTROL_COUNT = 110

    def __init__(
        self,
        project_root: Path,
        output_path: Path | None = None,
    ) -> None:
        self.project_root = project_root.resolve()

        self.controls_path = (
            self.project_root
            / "data"
            / "controls"
            / "cmmc_level2_controls.csv"
        )

        self.output_path = output_path or (
            self.project_root
            / "output"
            / "CMMC_Assessment_v0.1.xlsx"
        )

        self.styles = WorkbookStyles()
        self.factory = WorksheetFactory(self.styles)

    def build(self) -> Path:
        controls = self._load_controls()

        workbook = Workbook()
        self.styles.configure_workbook(workbook)

        default_sheet = workbook.active
        workbook.remove(default_sheet)

        worksheets = {
            sheet_name: workbook.create_sheet(
                title=sheet_name
            )
            for sheet_name in self.SHEET_ORDER
        }

        self._build_cover(
            worksheets["Cover"]
        )

        self._build_dashboard(
            worksheets["Dashboard"]
        )

        self._build_assessment(
            worksheets["Assessment"],
            controls,
        )

        self._build_domain_summary(
            worksheets["Domain Summary"],
            controls,
        )

        self._build_placeholder_sheet(
            worksheets["Evidence"],
            title="Evidence Register",
            subtitle=(
                "Track documents, configurations, interviews, "
                "tests, screenshots, and supporting evidence."
            ),
        )

        self._build_placeholder_sheet(
            worksheets["POA&M"],
            title="Plan of Action & Milestones",
            subtitle=(
                "Track remediation actions for requirements "
                "assessed as NOT MET."
            ),
        )

        self._build_placeholder_sheet(
            worksheets["SSP Crosswalk"],
            title="SSP Crosswalk",
            subtitle=(
                "Map CMMC requirements to System Security "
                "Plan sections, policies, procedures, and owners."
            ),
        )

        self._build_placeholder_sheet(
            worksheets["Assessment History"],
            title="Assessment History",
            subtitle=(
                "Store assessment snapshots and track score "
                "and readiness trends."
            ),
        )

        self._build_placeholder_sheet(
            worksheets["Executive Report"],
            title="Executive Report",
            subtitle=(
                "Printable management summary of assessment "
                "results, risks, and remediation priorities."
            ),
        )

        self._build_settings(
            worksheets["Settings"]
        )

        self._build_lists(
            worksheets["_Lists"]
        )

        worksheets["_Lists"].sheet_state = "veryHidden"

        workbook.active = workbook.sheetnames.index(
            "Cover"
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        workbook.save(self.output_path)

        return self.output_path

    def _load_controls(
        self,
    ) -> List[Dict[str, str]]:
        if not self.controls_path.exists():
            raise FileNotFoundError(
                "Compiled controls CSV was not found: "
                f"{self.controls_path}. "
                "Run python compile_guide.py first."
            )

        with self.controls_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            controls = list(
                csv.DictReader(file)
            )

        if (
            len(controls)
            != self.EXPECTED_CONTROL_COUNT
        ):
            raise ValueError(
                "Expected "
                f"{self.EXPECTED_CONTROL_COUNT} "
                "compiled CMMC requirements, "
                f"but found {len(controls)}."
            )

        required_columns = {
            "domain_code",
            "requirement_id",
            "title",
            "statement",
            "source_page_start",
            "source_page_end",
        }

        actual_columns = set(
            controls[0].keys()
        )

        missing_columns = (
            required_columns - actual_columns
        )

        if missing_columns:
            raise ValueError(
                "Compiled controls CSV is missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        return controls

    def _build_cover(
        self,
        worksheet: Worksheet,
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet,
            zoom_scale=90,
        )

        self.factory.create_title_band(
            worksheet,
            title="CMMC Level 2 Assessment Platform",
            subtitle=(
                "Readiness, evidence, POA&M, SSP mapping, "
                "and SPRS assessment workbook"
            ),
            end_column=10,
        )

        fields = [
            ("Organization Name", ""),
            ("Assessment Scope", ""),
            ("CAGE Code", ""),
            (
                "Assessment Type",
                "Level 2 Self-Assessment",
            ),
            ("Assessment Date", ""),
            ("Lead Assessor", ""),
            ("Workbook Version", "0.1"),
            (
                "Assessment Guide",
                "Level 2 Version 2.13",
            ),
        ]

        start_row = 6

        for offset, field in enumerate(fields):
            label, value = field
            row = start_row + offset

            label_cell = worksheet.cell(
                row=row,
                column=2,
            )

            value_cell = worksheet.cell(
                row=row,
                column=3,
            )

            label_cell.value = label
            value_cell.value = value

            label_cell.font = (
                self.styles.header_font()
            )
            label_cell.fill = (
                self.styles.section_fill()
            )
            label_cell.border = (
                self.styles.thin_border()
            )
            label_cell.alignment = (
                self.styles.left_alignment()
            )

            value_cell.fill = (
                self.styles.input_fill()
            )
            value_cell.font = (
                self.styles.input_font()
            )
            value_cell.protection = (
                self.styles.unlocked_protection()
            )
            value_cell.border = (
                self.styles.thin_border()
            )
            value_cell.alignment = (
                self.styles.left_alignment()
            )

        worksheet["B16"] = (
            "Instructions"
        )
        worksheet["B16"].font = (
            self.styles.section_font()
        )
        worksheet["B16"].fill = (
            self.styles.section_fill()
        )

        worksheet.merge_cells(
            start_row=17,
            start_column=2,
            end_row=20,
            end_column=8,
        )

        instruction_cell = worksheet["B17"]
        instruction_cell.value = (
            "Complete the organization metadata above, "
            "then use the Assessment worksheet to evaluate "
            "all 110 CMMC Level 2 requirements. Yellow cells "
            "are intended for user input. Gray cells contain "
            "formulas or system-generated values."
        )
        instruction_cell.font = (
            self.styles.body_font()
        )
        instruction_cell.fill = (
            self.styles.subheader_fill()
        )
        instruction_cell.border = (
            self.styles.thin_border()
        )
        instruction_cell.alignment = (
            self.styles.left_alignment()
        )

        widths = {
            "A": 3,
            "B": 24,
            "C": 45,
            "D": 4,
            "E": 18,
            "F": 18,
            "G": 18,
            "H": 18,
            "I": 18,
            "J": 18,
        }

        for column, width in widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

    def _build_dashboard(
        self,
        worksheet: Worksheet,
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet,
            zoom_scale=90,
        )

        self.factory.create_title_band(
            worksheet,
            title="Executive Dashboard",
            subtitle=(
                "Assessment readiness and compliance summary"
            ),
            end_column=13,
        )

        first_row = self.FIRST_ASSESSMENT_ROW
        last_row = (
            first_row
            + self.EXPECTED_CONTROL_COUNT
            - 1
        )

        cards = [
            (
                "Current Score",
                (
                    "=110-SUM("
                    f"Assessment!J{first_row}:"
                    f"J{last_row})"
                ),
            ),
            (
                "Requirements Met",
                (
                    '=COUNTIF('
                    f'Assessment!H{first_row}:'
                    f'H{last_row},"MET")'
                ),
            ),
            (
                "Requirements Not Met",
                (
                    '=COUNTIF('
                    f'Assessment!H{first_row}:'
                    f'H{last_row},"NOT MET")'
                ),
            ),
            (
                "Not Assessed",
                (
                    '=COUNTIF('
                    f'Assessment!H{first_row}:'
                    f'H{last_row},"NOT ASSESSED")'
                ),
            ),
        ]

        start_columns = [
            2,
            5,
            8,
            11,
        ]

        for card, start_column in zip(
            cards,
            start_columns,
        ):
            label, formula = card

            worksheet.merge_cells(
                start_row=6,
                start_column=start_column,
                end_row=6,
                end_column=start_column + 1,
            )

            worksheet.merge_cells(
                start_row=7,
                start_column=start_column,
                end_row=9,
                end_column=start_column + 1,
            )

            label_cell = worksheet.cell(
                row=6,
                column=start_column,
            )

            value_cell = worksheet.cell(
                row=7,
                column=start_column,
            )

            label_cell.value = label
            label_cell.font = (
                self.styles.header_font()
            )
            label_cell.fill = (
                self.styles.header_fill()
            )
            label_cell.alignment = (
                self.styles.center_alignment()
            )
            label_cell.border = (
                self.styles.thin_border()
            )

            value_cell.value = formula
            value_cell.font = (
                self.styles.title_font()
            )
            value_cell.fill = (
                self.styles.section_fill()
            )
            value_cell.alignment = (
                self.styles.center_alignment()
            )
            value_cell.border = (
                self.styles.thin_border()
            )

        worksheet["B12"] = (
            "Assessment Completion"
        )
        worksheet["B12"].font = (
            self.styles.header_font()
        )
        worksheet["B12"].fill = (
            self.styles.header_fill()
        )

        worksheet["C12"] = (
            '=IFERROR('
            f'(COUNTIF(Assessment!H{first_row}:'
            f'H{last_row},"MET")+'
            f'COUNTIF(Assessment!H{first_row}:'
            f'H{last_row},"NOT MET")+'
            f'COUNTIF(Assessment!H{first_row}:'
            f'H{last_row},"NOT APPLICABLE"))/'
            f'{self.EXPECTED_CONTROL_COUNT},0)'
        )
        worksheet["C12"].number_format = "0%"
        worksheet["C12"].fill = (
            self.styles.formula_fill()
        )
        worksheet["C12"].border = (
            self.styles.thin_border()
        )

        worksheet["E12"] = (
            "Evidence Complete"
        )
        worksheet["E12"].font = (
            self.styles.header_font()
        )
        worksheet["E12"].fill = (
            self.styles.header_fill()
        )

        worksheet["F12"] = (
            '=COUNTIF('
            f'Assessment!K{first_row}:'
            f'K{last_row},"Complete")'
        )
        worksheet["F12"].fill = (
            self.styles.formula_fill()
        )
        worksheet["F12"].border = (
            self.styles.thin_border()
        )

        worksheet["H12"] = (
            "POA&M Items"
        )
        worksheet["H12"].font = (
            self.styles.header_font()
        )
        worksheet["H12"].fill = (
            self.styles.header_fill()
        )

        worksheet["I12"] = (
            '=COUNTIF('
            f'Assessment!O{first_row}:'
            f'O{last_row},"Yes")'
        )
        worksheet["I12"].fill = (
            self.styles.formula_fill()
        )
        worksheet["I12"].border = (
            self.styles.thin_border()
        )

        for column in range(1, 14):
            column_letter = get_column_letter(
                column
            )
            worksheet.column_dimensions[
                column_letter
            ].width = 12

    def _build_assessment(
        self,
        worksheet: Worksheet,
        controls: List[Dict[str, str]],
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet,
            freeze_cell="A6",
            show_gridlines=False,
            zoom_scale=80,
        )

        self.factory.create_title_band(
            worksheet,
            title=(
                "CMMC Level 2 Requirement Assessment"
            ),
            subtitle=(
                "Complete status, evidence, ownership, "
                "SSP mapping, and assessor notes for all "
                "110 requirements."
            ),
            end_column=15,
        )

        headers = [
            "Domain",
            "Requirement ID",
            "Title",
            "Requirement Statement",
            "Source Start",
            "Source End",
            "Applicable",
            "Status",
            "Deduction",
            "Lost Points",
            "Evidence Status",
            "Control Owner",
            "SSP Reference",
            "Assessor Notes",
            "POA&M Required",
        ]

        header_row = 5

        for column, header in enumerate(
            headers,
            start=1,
        ):
            worksheet.cell(
                row=header_row,
                column=column,
            ).value = header

        self.factory.style_table_header(
            worksheet,
            row_number=header_row,
            start_column=1,
            end_column=len(headers),
        )

        first_data_row = (
            self.FIRST_ASSESSMENT_ROW
        )

        for row_offset, control in enumerate(
            controls
        ):
            row = (
                first_data_row
                + row_offset
            )

            worksheet.cell(
                row=row,
                column=1,
                value=control["domain_code"],
            )

            worksheet.cell(
                row=row,
                column=2,
                value=control["requirement_id"],
            )

            worksheet.cell(
                row=row,
                column=3,
                value=control["title"],
            )

            worksheet.cell(
                row=row,
                column=4,
                value=control["statement"],
            )

            worksheet.cell(
                row=row,
                column=5,
                value=int(
                    control[
                        "source_page_start"
                    ]
                ),
            )

            worksheet.cell(
                row=row,
                column=6,
                value=int(
                    control[
                        "source_page_end"
                    ]
                ),
            )

            worksheet.cell(
                row=row,
                column=7,
                value="Yes",
            )

            worksheet.cell(
                row=row,
                column=8,
                value="NOT ASSESSED",
            )

            worksheet.cell(
                row=row,
                column=9,
                value=1,
            )

            worksheet.cell(
                row=row,
                column=10,
                value=(
                    f'=IF('
                    f'OR(H{row}="MET",'
                    f'H{row}="NOT APPLICABLE"),'
                    f'0,IF(H{row}="NOT MET",'
                    f'I{row},0))'
                ),
            )

            worksheet.cell(
                row=row,
                column=11,
                value="Not Started",
            )

            worksheet.cell(
                row=row,
                column=12,
                value="",
            )

            worksheet.cell(
                row=row,
                column=13,
                value="",
            )

            worksheet.cell(
                row=row,
                column=14,
                value="",
            )

            worksheet.cell(
                row=row,
                column=15,
                value=(
                    f'=IF(H{row}="NOT MET",'
                    f'"Yes","No")'
                ),
            )

            for column in range(
                1,
                len(headers) + 1,
            ):
                cell = worksheet.cell(
                    row=row,
                    column=column,
                )

                cell.border = (
                    self.styles.thin_border()
                )
                cell.alignment = (
                    self.styles.left_alignment()
                )
                cell.font = (
                    self.styles.body_font()
                )

            for input_column in [
                7,
                8,
                11,
                12,
                13,
                14,
            ]:
                cell = worksheet.cell(
                    row=row,
                    column=input_column,
                )

                cell.fill = (
                    self.styles.input_fill()
                )
                cell.protection = (
                    self.styles.unlocked_protection()
                )

            for formula_column in [
                10,
                15,
            ]:
                worksheet.cell(
                    row=row,
                    column=formula_column,
                ).fill = (
                    self.styles.formula_fill()
                )

        last_data_row = (
            first_data_row
            + len(controls)
            - 1
        )

        status_validation = DataValidation(
            type="list",
            formula1=(
                '"MET,NOT MET,'
                'NOT APPLICABLE,'
                'NOT ASSESSED"'
            ),
            allow_blank=False,
        )

        worksheet.add_data_validation(
            status_validation
        )

        status_validation.add(
            f"H{first_data_row}:"
            f"H{last_data_row}"
        )

        applicable_validation = DataValidation(
            type="list",
            formula1='"Yes,No"',
            allow_blank=False,
        )

        worksheet.add_data_validation(
            applicable_validation
        )

        applicable_validation.add(
            f"G{first_data_row}:"
            f"G{last_data_row}"
        )

        evidence_validation = DataValidation(
            type="list",
            formula1=(
                '"Not Started,In Progress,'
                'Complete,Not Applicable"'
            ),
            allow_blank=False,
        )

        worksheet.add_data_validation(
            evidence_validation
        )

        evidence_validation.add(
            f"K{first_data_row}:"
            f"K{last_data_row}"
        )

        worksheet.conditional_formatting.add(
            (
                f"H{first_data_row}:"
                f"H{last_data_row}"
            ),
            FormulaRule(
                formula=[
                    f'H{first_data_row}="MET"'
                ],
                fill=self.styles.good_fill(),
            ),
        )

        worksheet.conditional_formatting.add(
            (
                f"H{first_data_row}:"
                f"H{last_data_row}"
            ),
            FormulaRule(
                formula=[
                    f'H{first_data_row}="NOT MET"'
                ],
                fill=self.styles.bad_fill(),
            ),
        )

        worksheet.conditional_formatting.add(
            (
                f"H{first_data_row}:"
                f"H{last_data_row}"
            ),
            FormulaRule(
                formula=[
                    (
                        f'H{first_data_row}'
                        '="NOT ASSESSED"'
                    )
                ],
                fill=(
                    self.styles.warning_fill()
                ),
            ),
        )

        widths = {
            "A": 10,
            "B": 18,
            "C": 34,
            "D": 65,
            "E": 12,
            "F": 12,
            "G": 12,
            "H": 18,
            "I": 12,
            "J": 12,
            "K": 18,
            "L": 22,
            "M": 20,
            "N": 45,
            "O": 16,
        }

        for column, width in widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

        worksheet.auto_filter.ref = (
            f"A{header_row}:"
            f"O{last_data_row}"
        )

        worksheet.print_title_rows = (
            f"1:{header_row}"
        )

    def _build_domain_summary(
        self,
        worksheet: Worksheet,
        controls: List[Dict[str, str]],
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet,
            freeze_cell="A6",
        )

        self.factory.create_title_band(
            worksheet,
            title="Domain Summary",
            subtitle=(
                "Requirement completion and findings "
                "by CMMC domain"
            ),
            end_column=8,
        )

        headers = [
            "Domain",
            "Requirement Count",
            "Met",
            "Not Met",
            "Not Assessed",
            "Lost Points",
            "Completion %",
            "Readiness",
        ]

        for column, header in enumerate(
            headers,
            start=1,
        ):
            worksheet.cell(
                row=5,
                column=column,
                value=header,
            )

        self.factory.style_table_header(
            worksheet,
            row_number=5,
            start_column=1,
            end_column=len(headers),
        )

        domain_codes: List[str] = []

        for control in controls:
            domain_code = (
                control["domain_code"]
            )

            if domain_code not in domain_codes:
                domain_codes.append(
                    domain_code
                )

        first_assessment_row = (
            self.FIRST_ASSESSMENT_ROW
        )

        last_assessment_row = (
            first_assessment_row
            + self.EXPECTED_CONTROL_COUNT
            - 1
        )

        for offset, domain_code in enumerate(
            domain_codes
        ):
            row = 6 + offset

            worksheet.cell(
                row=row,
                column=1,
                value=domain_code,
            )

            worksheet.cell(
                row=row,
                column=2,
                value=(
                    '=COUNTIF('
                    f'Assessment!$A$'
                    f'{first_assessment_row}:'
                    f'$A${last_assessment_row},'
                    f'A{row})'
                ),
            )

            worksheet.cell(
                row=row,
                column=3,
                value=(
                    '=COUNTIFS('
                    f'Assessment!$A$'
                    f'{first_assessment_row}:'
                    f'$A${last_assessment_row},'
                    f'A{row},'
                    f'Assessment!$H$'
                    f'{first_assessment_row}:'
                    f'$H${last_assessment_row},'
                    '"MET")'
                ),
            )

            worksheet.cell(
                row=row,
                column=4,
                value=(
                    '=COUNTIFS('
                    f'Assessment!$A$'
                    f'{first_assessment_row}:'
                    f'$A${last_assessment_row},'
                    f'A{row},'
                    f'Assessment!$H$'
                    f'{first_assessment_row}:'
                    f'$H${last_assessment_row},'
                    '"NOT MET")'
                ),
            )

            worksheet.cell(
                row=row,
                column=5,
                value=(
                    '=COUNTIFS('
                    f'Assessment!$A$'
                    f'{first_assessment_row}:'
                    f'$A${last_assessment_row},'
                    f'A{row},'
                    f'Assessment!$H$'
                    f'{first_assessment_row}:'
                    f'$H${last_assessment_row},'
                    '"NOT ASSESSED")'
                ),
            )

            worksheet.cell(
                row=row,
                column=6,
                value=(
                    '=SUMIF('
                    f'Assessment!$A$'
                    f'{first_assessment_row}:'
                    f'$A${last_assessment_row},'
                    f'A{row},'
                    f'Assessment!$J$'
                    f'{first_assessment_row}:'
                    f'$J${last_assessment_row})'
                ),
            )

            worksheet.cell(
                row=row,
                column=7,
                value=(
                    f'=IF(B{row}=0,0,'
                    f'C{row}/B{row})'
                ),
            )

            worksheet.cell(
                row=row,
                column=8,
                value=(
                    f'=IF(G{row}=1,'
                    f'"Ready",'
                    f'IF(G{row}>=0.8,'
                    f'"Near Ready",'
                    f'"Needs Work"))'
                ),
            )

            for column in range(1, 9):
                cell = worksheet.cell(
                    row=row,
                    column=column,
                )

                cell.border = (
                    self.styles.thin_border()
                )
                cell.alignment = (
                    self.styles.center_alignment()
                )
                cell.font = (
                    self.styles.body_font()
                )

            worksheet.cell(
                row=row,
                column=7,
            ).number_format = "0%"

        for column in range(1, 9):
            column_letter = (
                get_column_letter(column)
            )

            worksheet.column_dimensions[
                column_letter
            ].width = 18

        last_domain_row = (
            5 + len(domain_codes)
        )

        worksheet.auto_filter.ref = (
            f"A5:H{last_domain_row}"
        )

    def _build_settings(
        self,
        worksheet: Worksheet,
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet
        )

        self.factory.create_title_band(
            worksheet,
            title="Workbook Settings",
            subtitle=(
                "Organization-level configuration and "
                "workbook metadata"
            ),
            end_column=8,
        )

        settings = [
            ("Workbook Version", "0.1"),
            (
                "Assessment Guide Version",
                "2.13",
            ),
            ("Maximum SPRS Score", 110),
            ("Minimum SPRS Score", -203),
            (
                "Assessment Level",
                "CMMC Level 2",
            ),
            (
                "Workbook Generated By",
                "CMMC Assessment Platform",
            ),
        ]

        for offset, setting in enumerate(
            settings
        ):
            name, value = setting
            row = 6 + offset

            name_cell = worksheet.cell(
                row=row,
                column=2,
                value=name,
            )

            value_cell = worksheet.cell(
                row=row,
                column=3,
                value=value,
            )

            name_cell.fill = (
                self.styles.section_fill()
            )
            name_cell.font = (
                self.styles.header_font()
            )
            name_cell.border = (
                self.styles.thin_border()
            )

            value_cell.fill = (
                self.styles.input_fill()
            )
            value_cell.font = (
                self.styles.input_font()
            )
            value_cell.border = (
                self.styles.thin_border()
            )
            value_cell.protection = (
                self.styles.unlocked_protection()
            )

        worksheet.column_dimensions[
            "B"
        ].width = 30

        worksheet.column_dimensions[
            "C"
        ].width = 35

    def _build_lists(
        self,
        worksheet: Worksheet,
    ) -> None:
        worksheet["A1"] = (
            "Assessment Status"
        )

        statuses = [
            "MET",
            "NOT MET",
            "NOT APPLICABLE",
            "NOT ASSESSED",
        ]

        for index, status in enumerate(
            statuses,
            start=2,
        ):
            worksheet.cell(
                row=index,
                column=1,
                value=status,
            )

        worksheet["B1"] = (
            "Evidence Status"
        )

        evidence_statuses = [
            "Not Started",
            "In Progress",
            "Complete",
            "Not Applicable",
        ]

        for index, status in enumerate(
            evidence_statuses,
            start=2,
        ):
            worksheet.cell(
                row=index,
                column=2,
                value=status,
            )

        worksheet["C1"] = "Yes / No"

        worksheet["C2"] = "Yes"
        worksheet["C3"] = "No"

    def _build_placeholder_sheet(
        self,
        worksheet: Worksheet,
        title: str,
        subtitle: str,
    ) -> None:
        self.factory.configure_standard_sheet(
            worksheet
        )

        self.factory.create_title_band(
            worksheet,
            title=title,
            subtitle=subtitle,
            end_column=10,
        )

        worksheet.merge_cells(
            start_row=6,
            start_column=2,
            end_row=8,
            end_column=8,
        )

        placeholder_cell = worksheet["B6"]

        placeholder_cell.value = (
            "This module will be implemented in "
            "the next workbook sprint."
        )

        placeholder_cell.font = (
            self.styles.body_font()
        )
        placeholder_cell.fill = (
            self.styles.subheader_fill()
        )
        placeholder_cell.border = (
            self.styles.thin_border()
        )
        placeholder_cell.alignment = (
            self.styles.center_alignment()
        )

        for column in range(1, 11):
            column_letter = (
                get_column_letter(column)
            )

            worksheet.column_dimensions[
                column_letter
            ].width = 14