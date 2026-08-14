# Omni Local Pilot Acceptance Register — RC1

**Scope:** Local-only synthetic pilot. No client data. No public deployment.

| ID | Scenario | Expected result | Verification | Result |
|---|---|---|---|---|
| UAT-01 | Authentication and lockout | Valid login succeeds; repeated failures lock temporarily | Automated | PASS |
| UAT-02 | Organization tenant isolation | Users cannot access another tenant | Automated | PASS |
| UAT-03 | Invitation lifecycle | Secure, expiring, single-use invitation creates membership | Automated | PASS |
| UAT-04 | Role and assessment access | Explicit grants restrict non-administrators; admins retain oversight | Automated | PASS |
| UAT-05 | Multi-framework assessment | Frameworks can be selected and independently reported | Automated | PASS |
| UAT-06 | Assessment planning | Dates, scope, locations, team, and sampling persist | Automated | PASS |
| UAT-07 | Objective execution | Objective conclusions derive conservative control outcomes | Automated | PASS |
| UAT-08 | Evidence lifecycle | Request, upload/link, review, rejection reason, and audit history work | Automated | PASS |
| UAT-09 | Remediation lifecycle | Finding, owner, milestones, evidence, validation, and closure work | Automated | PASS |
| UAT-10 | Notifications | Immediate, suppressed, digest, reminder, and escalation paths work | Automated | PASS |
| UAT-11 | Quality and sign-off | Approval gates sign-off; completed assessment locks and can be audited/reopened | Automated | PASS |
| UAT-12 | Executive analytics | Scores, completion, exposure, domains, owners, and CSV drill-down agree | Automated | PASS |
| UAT-13 | Assessment workbook | Demographics, results, objectives, evidence, and remediation export | Automated | PASS |
| UAT-14 | Word Security Plan | Approved template binding, findings/conformity, artifacts, and Section 0 | Automated | PASS |
| UAT-15 | Complete package | Workbook, SSP, remediation plan, manifest, evidence, and URL records included | Automated | PASS |
| UAT-16 | Backup integrity | Database/evidence archive and SHA-256 verification pass | Automated + local execution | PASS |
| UAT-17 | Password recovery | Generic response and signed reset link do not expose account existence | Automated | PASS |
| UAT-18 | Security headers | CSP, clickjacking, MIME, permissions, and same-origin protections present | Automated | PASS |
| UAT-19 | Responsive visual walkthrough | Admin, assessor, client, and executive screens reviewed interactively | Manual browser confirmation | PENDING |

## Release decision

All automated critical and high-risk scenarios pass. RC1 is approved for continued
local pilot use with synthetic or expressly authorized non-production data. Public
deployment remains out of scope. UAT-19 is a visual confirmation item and does not
override automated functional acceptance.
