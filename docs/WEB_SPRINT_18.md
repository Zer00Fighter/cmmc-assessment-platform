# Sprint 18 — Operational Risk Management

Sprint 18 turns Omni's catalog risks and weighted control exposure into an organization-scoped risk-management workflow.

- Risks may originate from an assessment finding, the CCF Risk Catalog, or manual analysis.
- Each risk records affected controls, remediation plans, owner, status, category, and source.
- Likelihood and impact use a 1–5 scale; inherent risk is calculated as likelihood × impact.
- Residual likelihood and impact must be entered together and produce a separate residual score.
- Treatment choices are mitigate, accept, avoid, transfer, or undecided.
- Risk acceptance requires an organization administrator, rationale, and expiration date.
- Every create and update operation writes an immutable risk-history snapshot and organization audit event.
- The assessment dashboard and risk workspace show a true 5×5 likelihood-by-impact heatmap alongside the separate weighted control-exposure heatmap.
- Risk-register CSV exports include scores, treatment, dates, owners, controls, and remediation links.
- All screens and exports enforce organization and assessment tenant boundaries.

The CCF catalog continues to describe possible risks. Register entries represent an organization's evaluated risks.

## Sprint 18.1 — Guided finding-to-risk conversion

- Approved control-to-risk relationships are surfaced beside NOT MET controls in the risk workspace.
- Assessors can open a prefilled risk evaluation from an approved suggestion.
- Unapproved relationships cannot be used through the guided URL.
- Existing control/catalog combinations are marked as registered and cannot be duplicated.
