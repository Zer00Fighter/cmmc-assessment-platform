# Omni Word Security Plan Export

## Purpose

`export_ssp.py` creates a client-editable Word Security Plan (SSP) from an Omni
assessment workbook. It starts from a copy of an approved `.docx` template,
preserves that template's document package, and appends Omni's current Security
Plan crosswalk. The source template is never overwritten.

The initial template authority is the supplied NIST SP 800-171 / CMMC Level 2
SSP example. Its SHA-256 fingerprint at implementation time was:

`25903d727d6272073c4e5d888b3bb6c61f4c8d987961ef0356ea86c914cf76ad`

## Template contract

The source template provides the authoritative cover design, styles, headings,
tables, section configuration, headers, footers, numbering, image, and embedded
custom XML. Omni replaces literal `ACME` branding with the organization name
and adds two sections at the end:

1. **Omni Export Information** — organization, system/assessment, scope, CAGE
   code, owner, preparer, version, export date, and workbook version.
2. **Omni Security Plan Crosswalk** — one row per CMMC Level 2 requirement with
   its title, requirement statement, SSP reference, governance references,
   evidence references, owner, mapping status, and notes.

Missing organization-specific values are represented by
`[REQUIRES ORGANIZATION INPUT]`. This is deliberate: generated output is a
draft until an authorized owner completes and approves those values.

## Data mapping

| Word export field | Omni source |
|---|---|
| Organization and assessment metadata | `Cover` worksheet |
| Requirement ID, title, and statement | `Assessment` worksheet |
| Security Plan reference | `SSP Crosswalk` worksheet |
| Governance and evidence references | `SSP Crosswalk` worksheet |
| Control owner, mapping status, and notes | `SSP Crosswalk` worksheet |

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
