# Sprint 19.13 - SOC 2 Readiness Package and DRL Export

Sprint 19.13 packages the complete SOC 2 readiness-assessment record for client
delivery. The primary Word deliverable is the **SOC 2 Readiness Report**. The
work program remains the underlying assessment process and record.

## Standalone DRL

The package contains an Excel Document Request List with:

- request identifier, title, and description;
- request status, owner, due date, and notification setting;
- linked in-scope TSC criteria; and
- received evidence-artifact references.

The DRL is generated from the live assessment request register, including
requests created from the privately imported SOC 2 implementation guidance.
It can be downloaded directly from Report Center or obtained as an attachment
inside the complete readiness package.

## Readiness package

The downloadable ZIP includes:

- SOC 2 Readiness Report (`.docx`);
- standalone Document Request List (`.xlsx`);
- cross-framework traceability matrix (`.csv`);
- remediation-action register (`.xlsx`);
- Type I/Type II scope summary (`.json`);
- evidence index (`.csv`);
- uploaded evidence files;
- text records for external evidence URLs; and
- package manifest (`.json`).

The scope summary uses Omni's existing system description and assessment scope;
the SOC 2 profile does not duplicate a system-boundaries field.

## Integrity and privacy

Every package member except the manifest itself is listed with its byte size and
SHA-256 digest. Package generation is recorded in Omni's generated-document
history and audit log. Evidence is read from the private assessment storage at
generation time; no client evidence, DRL, organization data, or licensed source
content is added to Git.

## Acceptance gates

The same SOC 2 readiness gate used by the Word report controls package
generation. Automated tests validate DRL data binding, required ZIP members,
external-link records, evidence indexing, every manifest hash, HTTP download,
generated-document metadata, and auditability.
