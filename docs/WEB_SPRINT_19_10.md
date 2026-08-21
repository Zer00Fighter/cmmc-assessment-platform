# Sprint 19.10 - Points of Focus and Test Procedures

Sprint 19.10 extends the AICPA Trust Services Criteria assessment with
criterion-level execution, reusable test procedures, examination conclusions,
and sample-period controls. The implementation continues to use Omni's
framework-neutral objective execution engine.

## Criterion execution

Each of the 61 TSC criteria receives one Omni execution objective and five
Omni-authored suggested procedures:

- examine documentation and evidence;
- interview responsible personnel;
- observe the control in operation;
- test selected items or transactions; and
- reperform the control or calculation when appropriate.

The suggestions are starting points. Assessors can add assessment-specific
procedure customizations without changing the reusable framework catalog.
`Assessor Notes/Findings` remains the narrative field for conformity statements,
exceptions, and findings.

## Type I and Type II conclusions

Type I execution records design and implementation conclusions. Operating
effectiveness is set to not applicable because a Type I examination is measured
as of a date.

Type II execution records design, implementation, and operating-effectiveness
conclusions. Samples require a start and end date and must fall within the
configured examination period.

## Points of Focus and licensed content

Omni treats AICPA Points of Focus as considerations supporting a criterion, not
as separate mandatory criteria. The public repository intentionally contains no
licensed AICPA Point of Focus text.

An organization that has an authorized source can privately import a CSV,
XLSX, or XLSM file. The source must identify the TSC criterion, Point of Focus
identifier, and Point of Focus text. Source reference and page columns are
optional. Omni records the source filename, SHA-256 digest, row or page, and
reference for provenance without copying the source file into the repository.

Preview an import:

```powershell
.\.venv\Scripts\python.exe manage.py import_soc2_points_of_focus "C:\authorized\points-of-focus.xlsx"
```

Commit the validated rows to the private application database:

```powershell
.\.venv\Scripts\python.exe manage.py import_soc2_points_of_focus "C:\authorized\points-of-focus.xlsx" --commit
```

## Installation and verification

Apply the database migration and install the execution catalog:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_soc2_procedures
```

The seed is idempotent. It produces 61 criterion objectives and 305 suggested
procedures, and backfills objective results for existing TSC assessments.
