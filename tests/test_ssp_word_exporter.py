from __future__ import annotations

import hashlib
from pathlib import Path

from docx import Document
from openpyxl import Workbook

from src.ssp_export import SSPExportMetadata, export_ssp
from src.ssp_export.word_exporter import INPUT_REQUIRED


def _create_template(path: Path) -> None:
    document = Document()
    document.add_heading("ACME System Security Plan", level=0)
    document.add_paragraph("Prepared for ACME")
    document.sections[0].header.paragraphs[0].text = "ACME SSP"
    document.save(path)


def _create_workbook(path: Path) -> None:
    workbook = Workbook()
    cover = workbook.active
    cover.title = "Cover"
    cover.cell(6, 2, "Organization Name")
    cover.cell(6, 3, "Workbook Organization")
    cover.cell(7, 2, "Assessment Name")
    cover.cell(7, 3, "Enterprise System")
    cover.cell(14, 2, "Workbook Version")
    cover.cell(14, 3, "1.0.0")

    assessment = workbook.create_sheet("Assessment")
    assessment.cell(5, 2, "Requirement ID")
    assessment.cell(6, 1, "AC")
    assessment.cell(6, 2, "AC.L2-3.1.1")
    assessment.cell(6, 3, "Authorized Access Control")
    assessment.cell(6, 4, "Limit access to authorized users and devices.")
    assessment.cell(6, 16, "Security Officer")
    assessment.cell(6, 17, "SSP 3.1.1")

    crosswalk = workbook.create_sheet("SSP Crosswalk")
    crosswalk.cell(5, 2, "Requirement ID")
    crosswalk.cell(6, 1, "AC")
    crosswalk.cell(6, 2, "AC.L2-3.1.1")
    crosswalk.cell(6, 3, "SSP 3.1.1")
    crosswalk.cell(6, 4, "Access Control Policy")
    crosswalk.cell(6, 5, "Access review records")
    crosswalk.cell(6, 6, "Security Officer")
    crosswalk.cell(6, 7, "Mapped")
    workbook.save(path)


def _all_text(document: Document) -> str:
    text = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            text.extend(cell.text for cell in row.cells)
    for section in document.sections:
        text.extend(paragraph.text for paragraph in section.header.paragraphs)
    return "\n".join(text)


def test_export_preserves_template_and_adds_omni_crosswalk(tmp_path: Path) -> None:
    template = tmp_path / "source.docx"
    workbook = tmp_path / "omni.xlsx"
    output = tmp_path / "export.docx"
    _create_template(template)
    _create_workbook(workbook)
    original_hash = hashlib.sha256(template.read_bytes()).hexdigest()

    result = export_ssp(
        template,
        workbook,
        output,
        SSPExportMetadata(organization_name="R!SC", prepared_by="Omni Team"),
    )

    assert result == output.resolve()
    assert hashlib.sha256(template.read_bytes()).hexdigest() == original_hash
    document = Document(output)
    text = _all_text(document)
    assert "ACME" not in text
    assert "R!SC System Security Plan" in text
    assert "Omni Export Information" in text
    assert "Omni Security Plan Crosswalk" in text
    assert "AC.L2-3.1.1" in text
    assert "Access Control Policy" in text
    assert INPUT_REQUIRED in text


def test_export_rejects_overwriting_source_template(tmp_path: Path) -> None:
    template = tmp_path / "source.docx"
    workbook = tmp_path / "omni.xlsx"
    _create_template(template)
    _create_workbook(workbook)

    try:
        export_ssp(template, workbook, template)
    except ValueError as error:
        assert "must differ" in str(error)
    else:
        raise AssertionError("Expected source-template overwrite to be rejected")
