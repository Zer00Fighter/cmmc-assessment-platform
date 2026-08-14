# Omni Local Pilot RC1 Release Notes

Omni RC1 delivers a local, end-to-end Governance, Risk, and Compliance assessment
platform centered on CMMC Level 2 / NIST SP 800-171, with framework-agnostic evidence
and remediation foundations.

## Included

- Organization, system, assessment, framework, and tenant management
- Control and objective-level execution with Examine, Interview, and Test procedures
- Evidence requests, private artifacts, links, review, and packaged evidence
- Remediation Action Plans, milestones, risk acceptance, validation, and exports
- Live executive dashboard, SPRS calculation, workbook, Word SSP, and complete ZIP
- Planning, quality review, sign-off locking, reopening, and full audit history
- In-app and Gmail notifications, governance, digests, reminders, and escalation
- Invitations, profiles, roles, assessment access, and access-review export
- Login protection, password recovery, security headers, logs, health checks, and backup

## Known limitations

- Local SQLite remains the supported pilot database; PostgreSQL is required before
  a public multi-user production deployment.
- Scheduled commands require Windows Task Scheduler or a future production scheduler.
- Malware scanning is an integration point, not an active local scanning service.
- Visual browser acceptance remains a manual confirmation when browser automation is
  unavailable.
- CMMC is the only fully seeded control framework. Additional frameworks must use the
  governed ingestion and evidence-curation process.

## Deployment boundary

RC1 is not published. DNS, `itrisc.com`, TLS certificates, public hosting, firewall
rules, and production infrastructure are unchanged.
