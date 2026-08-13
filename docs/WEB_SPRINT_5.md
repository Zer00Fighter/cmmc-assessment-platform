# Omni Web Sprint 5

Sprint 5 connects the web assessment database to Omni's client deliverables and
adds an authenticated Report Center.

## Delivered exports

- **Assessment workbook:** organization/system demographics, control statuses,
  implementation states, SPRS deductions, Assessor Notes/Findings, owners, SSP
  references, evidence register, evidence mappings, and remediation plans.
- **Word Security Plan:** generated through the existing approved SSP template
  engine, including Section 0 Assessment Summary, overall SPRS score, control
  conformity, findings/conformity statements, owners, and supporting artifacts.
- **Remediation workbook:** the 24-column Remediation Action Plan (POA&M)
  compatible export delivered in Sprint 4.
- **Complete ZIP package:** all three deliverables, an evidence index, uploaded
  evidence files, external-reference text records, and a JSON package manifest.

Each external evidence URL produces a text file containing the artifact ID and
title, URL, source, period covered, review status, assessor notes, linked
requests, linked controls, linked remediation plans, registration date, and
registrant. Omni records the link; it does not retrieve external content.

## Readiness

The Report Center shows assessment completion, blockers, and warnings before
generation. A completed SSP or complete package is blocked when required
demographics, assessed control results, Assessor Notes/Findings, or the private
Word template are missing. Missing SSP references and accepted supporting
evidence are visible warnings. The workbook and remediation workbook remain
available for work in progress.

## Private template configuration

Set `OMNI_SSP_TEMPLATE` to the approved Word template's absolute local path.
On Windows, `Run Omni Web.cmd` loads an optional `Omni.local.cmd` file before
starting Django. That local file is Git-ignored because its path may reveal
client or organization information.

## Security and public-repository boundary

- Exports are generated in memory or temporary directories and streamed to the
  authenticated tenant user. They are not saved in the repository.
- Generation history stores only metadata: filename, type, version, generator,
  timestamp, size, SHA-256 digest, and readiness snapshot. It stores no export.
- Evidence downloads and package generation use tenant-scoped database queries.
- Generation creates organization-scoped audit events.
- `private_uploads/`, the local database, `Omni.local.cmd`, organization files,
  evidence, generated workbooks, Word files, and ZIP packages are excluded from
  the public source repository.
