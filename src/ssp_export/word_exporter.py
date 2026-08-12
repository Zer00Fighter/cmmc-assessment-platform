"""Export Omni's Security Plan crosswalk into a Word SSP template."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.document import Document as DocumentType
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from openpyxl import load_workbook

INPUT_REQUIRED = "[REQUIRES ORGANIZATION INPUT]"


@dataclass(frozen=True)
class SSPExportMetadata:
    """Organization-specific values used to brand an SSP export."""

    organization_name: str = ""
    system_name: str = ""
    system_owner: str = ""
    prepared_by: str = ""
    version: str = "1.0"
    export_date: str = ""


@dataclass(frozen=True)
class SSPControlRow:
    domain: str
    requirement_id: str
    title: str
    statement: str
    ssp_reference: str
    governance_references: str
    evidence_references: str
    owner: str
    mapping_status: str
    notes: str


def _display(value: object, *, required: bool = True) -> str:
    if value is None or not str(value).strip():
        return INPUT_REQUIRED if required else ""
    text = str(value).strip()
    if text.startswith("="):
        return INPUT_REQUIRED if required else ""
    return text


def _workbook_value(formula_sheet, value_sheet, row: int, column: int) -> object:
    cached = value_sheet.cell(row, column).value
    if cached is not None:
        return cached
    return formula_sheet.cell(row, column).value


def _read_workbook(workbook_path: Path) -> tuple[dict[str, str], list[SSPControlRow]]:
    formulas = load_workbook(workbook_path, data_only=False, read_only=True)
    values = load_workbook(workbook_path, data_only=True, read_only=True)
    try:
        cover_f = formulas["Cover"]
        cover_v = values["Cover"]
        cover = {
            str(cover_f.cell(row, 2).value).strip(): _display(
                _workbook_value(cover_f, cover_v, row, 3), required=False
            )
            for row in range(1, cover_f.max_row + 1)
            if cover_f.cell(row, 2).value
        }

        assessment_f = formulas["Assessment"]
        assessment_v = values["Assessment"]
        assessment: dict[str, list[object]] = {}
        for row in range(6, assessment_f.max_row + 1):
            requirement_id = _display(assessment_f.cell(row, 2).value, required=False)
            if requirement_id:
                assessment[requirement_id] = [
                    _workbook_value(assessment_f, assessment_v, row, col)
                    for col in range(1, assessment_f.max_column + 1)
                ]

        crosswalk_f = formulas["SSP Crosswalk"]
        crosswalk_v = values["SSP Crosswalk"]
        rows: list[SSPControlRow] = []
        for row in range(6, crosswalk_f.max_row + 1):
            requirement_id = _display(crosswalk_f.cell(row, 2).value, required=False)
            if not requirement_id:
                continue
            source = assessment.get(requirement_id, [])
            rows.append(
                SSPControlRow(
                    domain=_display(crosswalk_f.cell(row, 1).value, required=False),
                    requirement_id=requirement_id,
                    title=_display(source[2] if len(source) > 2 else None),
                    statement=_display(source[3] if len(source) > 3 else None),
                    ssp_reference=_display(
                        _workbook_value(crosswalk_f, crosswalk_v, row, 3)
                    ),
                    governance_references=_display(
                        _workbook_value(crosswalk_f, crosswalk_v, row, 4)
                    ),
                    evidence_references=_display(
                        _workbook_value(crosswalk_f, crosswalk_v, row, 5)
                    ),
                    owner=_display(_workbook_value(crosswalk_f, crosswalk_v, row, 6)),
                    mapping_status=_display(
                        _workbook_value(crosswalk_f, crosswalk_v, row, 7)
                    ),
                    notes=_display(_workbook_value(crosswalk_f, crosswalk_v, row, 8)),
                )
            )
        return cover, rows
    finally:
        formulas.close()
        values.close()


def _iter_paragraphs(document: DocumentType) -> Iterable:
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    for section in document.sections:
        for container in (section.header, section.footer):
            yield from container.paragraphs
            for table in container.tables:
                for row in table.rows:
                    for cell in row.cells:
                        yield from cell.paragraphs


def _replace_literal(document: DocumentType, old: str, new: str) -> int:
    replacements = 0
    for paragraph in _iter_paragraphs(document):
        for run in paragraph.runs:
            if old in run.text:
                replacements += run.text.count(old)
                run.text = run.text.replace(old, new)
    return replacements


def _set_repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    properties.append(repeat)


def _shade_cell(cell, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_text(cell, text: str, *, bold: bool = False, size: float = 7.5) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def _add_metadata_table(
    document: DocumentType, metadata: SSPExportMetadata, cover: dict[str, str]
) -> None:
    values = [
        ("Organization", metadata.organization_name),
        (
            "System / Assessment",
            metadata.system_name or cover.get("Assessment Name", ""),
        ),
        ("Assessment Scope", cover.get("Assessment Scope", "")),
        ("CAGE Code", cover.get("CAGE Code", "")),
        ("System Owner", metadata.system_owner),
        ("Prepared By", metadata.prepared_by or cover.get("Lead Assessor", "")),
        ("Document Version", metadata.version),
        ("Export Date", metadata.export_date or date.today().isoformat()),
        ("Omni Workbook Version", cover.get("Workbook Version", "")),
    ]
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in values:
        cells = table.add_row().cells
        _set_cell_text(cells[0], label, bold=True, size=9)
        _shade_cell(cells[0], "D9EAF7")
        _set_cell_text(cells[1], _display(value), size=9)


def _add_crosswalk(document: DocumentType, rows: list[SSPControlRow]) -> None:
    section = document.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.45)
    section.right_margin = Inches(0.45)

    heading = document.add_heading("Omni Security Plan Crosswalk", level=1)
    heading.paragraph_format.keep_with_next = True
    paragraph = document.add_paragraph(
        "This appendix is generated from Omni. Bracketed markers identify content that "
        "must be completed or validated by the organization before approval."
    )
    paragraph.paragraph_format.space_after = Pt(6)

    headers = [
        "Requirement",
        "Requirement title and statement",
        "Security Plan reference",
        "Governance references",
        "Evidence references",
        "Owner / status / notes",
    ]
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    widths = [0.9, 3.25, 1.45, 1.7, 1.7, 1.55]
    header_cells = table.rows[0].cells
    _set_repeat_table_header(table.rows[0])
    for cell, label, width in zip(header_cells, headers, widths):
        cell.width = Inches(width)
        _set_cell_text(cell, label, bold=True, size=7.5)
        _shade_cell(cell, "1F4E78")
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = None
            run._element.get_or_add_rPr().append(_color_element("FFFFFF"))

    for item in rows:
        cells = table.add_row().cells
        values = [
            f"{item.requirement_id}\n({item.domain})",
            f"{item.title}\n{item.statement}",
            item.ssp_reference,
            item.governance_references,
            item.evidence_references,
            f"Owner: {item.owner}\nStatus: {item.mapping_status}\nNotes: {item.notes}",
        ]
        for cell, text, width in zip(cells, values, widths):
            cell.width = Inches(width)
            _set_cell_text(cell, text)


def _color_element(value: str):
    color = OxmlElement("w:color")
    color.set(qn("w:val"), value)
    return color


def export_ssp(
    template_path: str | Path,
    workbook_path: str | Path,
    output_path: str | Path,
    metadata: SSPExportMetadata | None = None,
) -> Path:
    """Create a Word SSP from an immutable template and an Omni workbook."""

    template = Path(template_path).resolve()
    workbook = Path(workbook_path).resolve()
    output = Path(output_path).resolve()
    if template == output:
        raise ValueError("Output path must differ from the source template path.")
    if not template.is_file():
        raise FileNotFoundError(f"SSP template not found: {template}")
    if not workbook.is_file():
        raise FileNotFoundError(f"Omni workbook not found: {workbook}")

    cover, rows = _read_workbook(workbook)
    if not rows:
        raise ValueError("The Omni workbook contains no SSP Crosswalk records.")

    supplied = metadata or SSPExportMetadata()
    organization = supplied.organization_name or cover.get("Organization Name", "")
    resolved = SSPExportMetadata(
        organization_name=_display(organization),
        system_name=supplied.system_name,
        system_owner=supplied.system_owner,
        prepared_by=supplied.prepared_by,
        version=supplied.version,
        export_date=supplied.export_date,
    )

    document = Document(template)
    _replace_literal(document, "ACME", resolved.organization_name)
    document.core_properties.title = (
        f"{resolved.organization_name} System Security Plan"
    )
    document.core_properties.subject = "Omni Security Plan (SSP) export"
    document.core_properties.comments = "Generated by Omni by R!SC"

    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    document.add_heading("Omni Export Information", level=1)
    _add_metadata_table(document, resolved, cover)
    _add_crosswalk(document, rows)

    output.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=".docx", dir=output.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        document.save(temporary)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output
