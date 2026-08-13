# Omni Word Security Plan Export

## Purpose

`export_ssp.py` creates a client-editable Word Security Plan (SSP) from an Omni
assessment workbook. It starts from a copy of an approved `.docx` template,
preserves that template's document package, and populates each practice's
existing **Supporting Artifacts** table. The source template is never
overwritten.

The initial template authority is the supplied NIST SP 800-171 / CMMC Level 2
SSP example. Its SHA-256 fingerprint at implementation time was:

`25903d727d6272073c4e5d888b3bb6c61f4c8d987961ef0356ea86c914cf76ad`

## Template contract

The source template provides the authoritative cover design, styles, headings,
tables, section configuration, headers, footers, numbering, image, and embedded
custom XML. Omni replaces literal `ACME` branding with the organization name
and adds an **SPRS Score** field to every control header, positioned between
**CMMC Level** and **Practice ID**. When the workbook is assessed, this field is
populated with the requirement's calculated SPRS deduction (0, 1, 3, or 5).

The exporter also binds the control-level MET, NOT MET, or NOT APPLICABLE result.
The `Objective Assessment` worksheet stores all 320 objective findings and
conformity statements and binds them into their corresponding Word rows. For
legacy workbooks without that worksheet, only MET and NOT APPLICABLE safely
propagate from the control result; NOT MET objectives remain unselected.

Omni also maps supporting evidence into the template's three artifact categories:

1. **System Design Documentation** — policies, plans, standards, procedures,
   and other governance references.
2. **System Configuration Settings and Associated Documentation** — explicitly
   marked for organization input until a configuration artifact is mapped.
3. **Supplemental Artifacts** — the evidence references recorded in Omni.

The exporter does not append assessment test procedures, governance columns,
mapping statuses, assessor notes, or a separate crosswalk to the SSP.

Missing organization-specific values are represented by
`[REQUIRES ORGANIZATION INPUT]`. This is deliberate: generated output is a
draft until an authorized owner completes and approves those values.

## Data mapping

| Word export field | Omni source |
|---|---|
| Organization and assessment metadata | `Cover` worksheet |
| Practice ID used to locate the template table | `Assessment` / `SSP Crosswalk` worksheets |
| Requirement conformity and SPRS deduction | `Assessment` worksheet |
| Objective conformity and narratives | `Objective Assessment` worksheet |
| System design documentation | Governance references in `SSP Crosswalk` |
| Supplemental artifacts | Evidence references in `SSP Crosswalk` |

Command-line metadata overrides the corresponding workbook value when supplied.

## Usage

```powershell
.\.venv\Scripts\python.exe export_ssp.py `
  --template "C:\path\to\SSP-template.docx" `
  --workbook "output\Omni_CMMC_Assessment_v1.0.xlsx" `
  --output "output\Omni_System_Security_Plan.docx" `
  --organization "Organization Name" `
  --system "System Name" `
  --system-owner "System Owner" `
  --prepared-by "Document Preparer" `
  --version "1.0"
```

The output path must differ from the source template path. The file is written
atomically so an interrupted export does not leave a partially written final
document.

## Validation status

The implementation verifies source-template immutability, required content,
organization replacement, missing-value markers, and overwrite protection.
The first real export retained all 34 package parts, including 12 custom XML
parts, one header, four footers, styles, numbering, and the embedded image.

Visual page rendering is still required on a workstation with Microsoft Word or
LibreOffice before treating a generated draft as publication-ready.
