# Sprint 18.2 — Optional Risk Treatment and Continuous Monitoring

Risk management remains an optional assessment capability and never affects control scoring, evidence readiness, quality review, or sign-off.

- `Enable Risk Management` controls all risk workspaces, catalog suggestions, treatment, monitoring, and both risk heatmaps. It defaults off.
- `Include Risk Management in Reports` separately controls risk deliverables in generated assessment packages. It defaults off and requires risk management to be enabled.
- Disabling either toggle preserves all previously recorded risk data.
- Treatment actions support owners, dependencies, dates, priorities, remediation links, completion validation, and evidence.
- Organization risk-tolerance policies control maximum residual score, critical-risk acceptance, maximum acceptance duration, and reminder windows.
- Residual reassessment records prior and new likelihood/impact, rationale, evidence, assessor, and timestamp.
- Risk acceptance uses a request and administrator review workflow with policy enforcement and expiration.
- Continuous monitoring records review frequency, dates, trend, notes, and trigger events.
- Daily workflow reminders cover risk treatment, periodic review, and acceptance expiration; expired acceptance returns the risk to monitoring.
- Closure requires completed treatment actions, residual evaluation, supporting evidence, and rationale. Reopening requires administrator authorization and history.
- The complete ZIP package includes `Omni-Risk-Register.csv` only when both assessment toggles are enabled.
