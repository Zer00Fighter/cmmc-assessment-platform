# Sprint 19.7 — Authoritative TSC Baseline

Sprint 19.7 adds a versioned AICPA Trust Services Criteria catalog boundary to Omni.

## Baseline

- Framework code: `AICPA-TSC-2017-RPOF-2022`
- Source: AICPA's 2017 Trust Services Criteria with revised Points of Focus (2022)
- Catalog: 61 official criterion identifiers across Security/Common Criteria,
  Availability, Processing Integrity, Confidentiality, and Privacy
- Scoring: none; SOC 2 conclusions are not inferred from a numeric score

The repository contains official criterion identifiers and hierarchy plus
Omni-authored descriptive labels. It deliberately does not reproduce AICPA's
copyrighted criterion wording or Points of Focus. Users must consult an
authorized copy of the AICPA publication for authoritative content.

## Integrity controls

The installer validates the exact identifier inventory, domain membership,
duplicates, unexpected identifiers, official-source URL, and copyright notice.
The version is immutable: an existing framework with the same code must have
the same source digest and exact identifier set.

Install or verify locally with:

```powershell
.\.venv\Scripts\python.exe manage.py seed_soc2_tsc
```

The source checklist workbook is not imported or committed in this sprint.
Practical control activities and their proposed mappings are Sprint 19.8.
