# Omni by R!SC

Omni is R!SC's governance, risk, and compliance platform. This repository currently provides Omni's CMMC Level 2 assessment workflow, including assessment readiness, evidence management, POA&M tracking, SSP mapping, and weighted scoring.

## Build the workbook

```powershell
.\.venv\Scripts\python.exe build.py
```

The default output is `output/Omni_CMMC_Assessment_v0.2.xlsx`.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
