# Sprint 18.3.1 — Illustrated User Manual

Sprint 18.3.1 adds a visual, end-to-end walkthrough to the framework-agnostic
Omni user and administrator manual.

## Delivered

- 16 application screenshots captured from an isolated synthetic database
- Eight concise walkthrough figures with numbered on-screen callouts and matching instructions
- Visual coverage from sign-in through assessment execution, evidence,
  remediation, quality review, reporting, optional risk, and administration
- Version 1.1 of `Omni-Comprehensive-User-and-Administrator-Manual.docx`
- `seed_manual_demo`, an idempotent management command that creates only
  fictional demonstration content for documentation and testing
- A fix for unassigned-assessor rendering on the objective execution screen

## Privacy boundary

The screenshots contain fictional organizations, systems, accounts, framework
requirements, artifacts, findings, remediation, and risks. The demo database,
generated annotated images, rendered pages, and runtime logs remain ignored.
No client records, organization files, private source workbooks, evidence,
credentials, or local database files are committed.

## Rebuild

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_omni_manual.py
```

The builder reads the committed synthetic screenshots, generates annotated
working images under `output/manual_assets`, and rebuilds the public Word
manual deterministically.
