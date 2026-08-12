# Omni by R!SC

Omni is R!SC's governance, risk, and compliance platform. This repository currently provides Omni's CMMC Level 2 assessment workflow, including assessment readiness, evidence management, POA&M tracking, SSP mapping, and weighted scoring.

## Build the workbook

```powershell
.\.venv\Scripts\python.exe build.py
```

The default output is `output/Omni_CMMC_Assessment_v0.2.xlsx`.

The implemented version 0.2 workflow has completed its documented
[CMMC end-to-end acceptance](docs/CMMC_END_TO_END_ACCEPTANCE.md).

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
