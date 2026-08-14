# Omni Web Sprint 7

Sprint 7 turns the assessment dashboard into a tenant-scoped executive and
operational analytics workspace. All values are calculated from live assessment
records; Omni does not persist a second analytics copy of organization data.

## Executive metrics

- Primary-framework score and framework-by-framework score cards
- Control completion with MET, NOT MET, NOT APPLICABLE, and NOT ASSESSED counts
- Objective-level completion based on Sprint 6 execution records
- Decision-readiness indicator and explicit blockers
- Quality-review and assessment-lock status

## Operational analytics

- Evidence acceptance rate and overdue evidence requests
- Open, overdue, and high-risk Remediation Action Plans
- Domain completion, findings, and score deductions
- Control-owner assignment, completion, and finding workload
- Engagement dates and the nearest evidence and remediation deadlines
- Framework and domain filters with drill-down links to execution, evidence,
  remediation, quality review, and individual control results

## Executive snapshot export

Authorized organization members can download a CSV snapshot containing the
assessment identity, status, quality-review state, and control-level framework,
requirement, domain, status, deduction, owner, and evidence counts. Export is
audited and streamed to the browser. It is not saved in the repository.

## Security and public-repository boundary

Every dashboard query begins with the authenticated user's organization scope.
Cross-tenant dashboard and export requests return HTTP 404. Organization names,
scores, findings, owners, deadlines, evidence, remediation records, generated
snapshots, and other runtime data must never be committed to the public repo.
Automated tests use synthetic organizations and assessment records only.
