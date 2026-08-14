# Sprint 12 — Comprehensive Controls Framework ingestion

Sprint 12 introduces governed, format-independent framework ingestion without making the private CCF source workbook part of the public repository.

## Workflow

1. A superuser opens **Framework catalog → Framework ingestion**.
2. Upload CSV, Excel (`.xlsx`/`.xlsm`), or a text-based PDF and enter version-specific framework metadata.
3. Omni creates a private dry-run record, normalizes requirements, hashes the source, and reports blocking issues.
4. Review the normalized preview and source row/page provenance.
5. Explicitly approve the import. Omni creates a new framework version and never overwrites an existing framework code.

PDF pages without extractable text are reported as requiring OCR. Mapping columns may identify a target framework, target requirement, and relationship. Resolved mappings are approved with the import; unresolved references remain visible in the normalized source record for later curation.

The framework catalog displays mapped-requirement coverage. Uploaded source files, database records, and generated reports are runtime data and must not be committed.
