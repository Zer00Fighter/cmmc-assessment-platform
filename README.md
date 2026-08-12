# Omni by R!SC

Omni is R!SC's governance, risk, and compliance platform. This repository
provides Omni's CMMC Level 2 assessment workflow, including assessment
readiness, evidence management, Remediation Action Plan (POA&M) tracking,
Security Plan (SSP) mapping, historical snapshots, executive reporting, and
weighted scoring.

## Build the workbook

```powershell
.\.venv\Scripts\python.exe build.py
```

The default output is `output/Omni_CMMC_Assessment_v1.0.xlsx`.

The v1 workflow builds on its documented
[CMMC end-to-end acceptance](docs/CMMC_END_TO_END_ACCEPTANCE.md). See the
[v1.0.0 release notes](docs/RELEASE_NOTES_v1.0.0.md) for the release scope and
known boundaries.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Terminology

Omni stores reusable GRC concepts under canonical names while displaying
framework terminology where it helps the assessor. For CMMC, Security Plan is
also shown as SSP and Remediation Action Plan is also shown as POA&M. These are
aliases, not separate objects.
