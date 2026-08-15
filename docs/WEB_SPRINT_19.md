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

## Remaining Sprint 19 workstreams

1. Continuous control monitoring and reassessment triggers
2. Approved baselines and period-over-period comparison
3. Program and portfolio dashboard
4. Compliance calendar and scheduled workflow automation
5. Continuous compliance reports and exports
6. External ticket event routing and later connector implementation
7. Security, regression, and synthetic acceptance testing
