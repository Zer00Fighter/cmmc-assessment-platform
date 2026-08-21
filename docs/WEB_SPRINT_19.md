# Sprint 19 — Continuous Compliance and Assessment Program Management

Sprint 19 turns Omni's end-to-end assessment capability into an ongoing
compliance program. Its approved scope includes reusable and recurring
assessments, evidence freshness, continuous control monitoring, baseline
comparison, portfolio analytics, workflow automation, program reporting, and
an external-ticketing integration foundation.

## Sprint 19.1 delivered foundation

- Organization-scoped assessment templates
- Framework and primary-framework preservation
- Scope, location, sampling, notification, and optional-risk configuration
- On-demand, monthly, quarterly, semiannual, and annual recurrence metadata
- Evidence-request blueprints derived from an authorized assessment
- Fresh assessment creation with explicit template and prior-assessment lineage
- Automatic framework control and objective loading
- Explicit prevention of copied results, findings, assessor notes, scores,
  evidence files, approvals, remediation decisions, and risk conclusions
- Organization-level integration delivery policy
- Jira, ServiceNow, and future-provider identifiers without credentials
- Connector-neutral outbound work-item synchronization ledger

## Authority and privacy boundaries

External tickets may coordinate future operational work, but Omni remains the
authoritative record for assessment conclusions, evidence acceptance, risk
decisions, quality review, and sign-off. Sprint 19.1 does not connect to an
external service and stores no API token, password, endpoint, or client file.

## Sprint 19.2 delivered evidence freshness and renewal

- Evidence-request validity periods and configurable renewal lead times
- Optional automatic renewal at the individual request level
- Explicit artifact effective and expiration dates
- Policy-derived deadlines when an explicit expiration date is not supplied
- Current, renew-soon, expired, undated, and superseded artifact states
- Evidence workspace freshness metrics, filters, deadlines, and renewal action
- Duplicate-safe renewal requests preserving owners, controls, catalog identity,
  notification preferences, and source-request lineage
- Scheduled renewal generation through the existing workflow reminder command
- Freshness warnings and deadline metadata in assessment exports

Renewal creates a new request; it never overwrites or copies an evidence file.
When replacement evidence is accepted, the prior artifact can be linked through
the existing supersession field, retaining a defensible evidence history.

## Sprint 19.3 delivered continuous control monitoring

- Optional control-level periodic review schedules, frequencies, owners, and notes
- Monitoring events for scheduled reviews, stale evidence, system changes,
  incidents, vulnerabilities, audit findings, and manual observations
- One governed reassessment task for every affected control
- Immutable snapshots of the prior conclusion, implementation state, score
  deduction, findings, and update timestamp
- Reassessment ownership, due dates, workflow status, resolution, and completion
  attribution
- Automatic reassessment triggers for scheduled reviews and expired evidence
- Duplicate-safe scheduled processing, reassessment assignment notifications,
  deadline reminders, audit events, and event history

Monitoring never changes a control conclusion automatically. The assessor opens
the control, performs and records the necessary assessment work, and then closes
the reassessment task with a documented outcome. This preserves decision authority
and makes the before-and-after trail explicit.

## Sprint 19.4 delivered approved baselines and comparison

- Baseline capture restricted to signed-off assessments with approved quality review
- Draft, approved, and retired baseline lifecycle with administrator approval
- Immutable JSON snapshots protected by deterministic SHA-256 checksums
- Preserved framework scores, control conclusions, implementation states,
  deductions, finding fingerprints, and accepted-evidence counts
- Same-system comparison against current assessment work without copying results
- Improved, regressed, changed, unchanged, new, and removed control classification
- Framework score deltas, accepted-evidence deltas, and finding-change indicators
- CSV comparison export containing the baseline checksum and full control traceability
- Audit history for baseline capture, approval, retirement, and export

Retiring a baseline removes it from active comparison without deleting its snapshot.
Reopening or changing the source assessment cannot rewrite the captured baseline.

## Sprint 19.5 delivered program and portfolio analytics

- Organization-level executive dashboard across authorized systems and assessments
- Filters for system, framework, assessment status, and system or assessment search
- Program metrics for assessment delivery, control completion, findings, evidence
  deadlines and freshness, remediation, control reassessment, and optional risk
- Latest-assessment posture for each visible system with direct drill-down
- Framework coverage and completion across single- and multi-framework assessments
- Recent assessment trend showing completion, findings, and framework-native scores
- Filter-preserving CSV portfolio snapshot with an organization audit record
- Assessment-grant-aware authorization for dashboard counts, labels, links, and exports

Portfolio analytics are calculated from Omni's authoritative records at request
time. No copied executive-data store can drift from the underlying assessment work.

## Sprint 19.6 delivered calendar and scheduled automation

- Unified, filterable compliance calendar across assessment, evidence,
  remediation, monitoring, recurrence, and optional-risk obligations
- Assessment-grant-aware calendar visibility and filter-preserving CSV export
- Disabled-by-default organization automation policy with daily or weekly cadence
- Organization-scoped runner for reminders, renewals, reassessments, and risk dates
- Duplicate-safe execution, run-now administration, run history, and audit events
- Safe Windows Task Scheduler launcher and configuration guidance without secrets

The operating-system task runs daily, while Omni determines which enabled
organizations are due. Existing notification and email policies remain authoritative.

## Remaining Sprint 19 workstreams

1. Continuous compliance reports and exports
2. External ticket event routing and later connector implementation
3. Security, regression, and synthetic acceptance testing
