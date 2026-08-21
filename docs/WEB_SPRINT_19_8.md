# Sprint 19.8 — SOC 2 Workbook Normalization and Mapping

Sprint 19.8 preserves the supplied SOC 2 readiness checklist as practical
implementation guidance beneath the authoritative TSC baseline from Sprint 19.7.

## Separation of meaning

- `Requirement` remains an authoritative framework criterion.
- `ImplementationActivity` stores a practical control activity, its original
  checklist identifier, classification, editable planning metadata, and exact
  workbook provenance.
- `ImplementationActivityMapping` links an activity to one or more TSC criteria.
- Every initial relationship is `SUPPORTS` and `PROPOSED`; it does not imply
  equivalence, audit satisfaction, or compliance.

This separation retains useful rows such as `CC8.2`, `CC8.3`, `CC9.3`, and the
`SEC`, `AVAIL`, `CONF`, `PI`, and `PRIV` identifiers without misrepresenting them
as official AICPA criterion identifiers.

## Multi-tab validation

The normalizer reads the complete `All Controls` master sheet and independently
validates all six category sheets. It blocks duplicate identifiers, missing
tabs, header changes, category/master inconsistencies, unmapped source rows,
and mapping targets that do not exist in the Sprint 19.7 identifier inventory.

The source workbook remains runtime data and is never committed to the public
repository. Its filename, SHA-256 digest, source sheet, and row number are stored
for traceability.

## Local workflow

Preview without changing the database:

```powershell
.\.venv\Scripts\python.exe manage.py import_soc2_activities `
  "D:\DWNLDS\soc-2-controls-list.xlsx"
```

Import the normalized activities and proposed mappings:

```powershell
.\.venv\Scripts\python.exe manage.py import_soc2_activities `
  "D:\DWNLDS\soc-2-controls-list.xlsx" --commit
```

Re-running the same source digest is idempotent. Mapping review and approval
remain governed follow-on work; importing never auto-approves a relationship.
