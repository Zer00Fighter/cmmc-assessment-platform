# Omni Web Sprint 4

Sprint 4 completes the operational assessment loop with a framework-agnostic
Remediation Action Plan. The familiar terms POA&M and Corrective Action Plan
remain supported aliases and appear in the compatible workbook export.

## Delivered workflow

1. Assessors can start a remediation plan directly from a NOT MET control. The
   control and Assessor Notes/Findings are carried into the new plan.
2. One plan can address multiple controls and includes weakness, root cause,
   corrective action, compensating controls, closure criteria, priority,
   severity, likelihood, calculated risk score, residual risk, and dates.
3. Plans have a primary owner, supporting owners, ordered milestones, milestone
   owners, schedules, completion status, and aging/overdue visibility.
4. Accepted assessment evidence can be linked as closure evidence. Closing a
   plan requires root cause, corrective action, closure criteria, completion
   date, closure evidence, and assessor validation.
5. Risk acceptance records include rationale, approving organization
   Administrator, and expiration. Only an Administrator can approve acceptance.
6. Assigned plan or milestone owners can update execution details but cannot
   self-validate closure. Administrators and Assessors manage all plans;
   Assessors validate closure.
7. Dashboard and remediation workspace statistics show open, overdue, and
   closed plans. Filters cover text, status, priority, control domain, owner,
   and overdue items.
8. The export produces the same 24 business columns used by Omni's workbook
   Remediation Action Plan (POA&M), including control mappings, risk, aging,
   validation, evidence IDs, SSP references, and assessor notes.

## Security and public-repository boundary

All remediation records remain in the runtime database and are not committed.
Closure artifacts use Sprint 3's private, tenant-scoped evidence storage. The
export is streamed to the authenticated user and is not saved inside the source
repository. Cross-tenant plan access returns HTTP 404, and create, update,
milestone, validation, and export activity is recorded in organization-scoped
audit events.

Organization/client data, assessment results, evidence, remediation plans, and
generated exports must never be committed to the public repository. Tests use
only synthetic organizations and findings.
