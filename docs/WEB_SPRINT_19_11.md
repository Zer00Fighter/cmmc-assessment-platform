# Sprint 19.11 - Evidence and Cross-Framework Reuse

Sprint 19.11 operationalizes SOC 2 evidence planning and connects it to Omni's
governed multi-framework reuse workflow. Evidence and prior testing may support
more than one framework, but every framework retains its own assessment
conclusion.

## SOC 2 evidence planning

The shared-work workspace reads the `Evidence Artifact`, `Evidence Source`, and
`Frequency` metadata retained from the privately imported SOC 2 implementation
workbook. It presents those entries as non-authoritative evidence suggestions
for in-scope TSC criteria.

An assessor selects the relevant suggestions and creates consolidated evidence
requests. Identical artifact titles become one request linked to all applicable
TSC criteria, with the expected source retained in its description. This avoids duplicate collection while preserving
criterion-level traceability. Rejected activity mappings are excluded.

The public repository contains neither the source workbook nor its private
evidence guidance. The feature operates on data already imported into the
private Omni database.

## Cross-framework reuse controls

Harmonization analysis now consumes only requirement mappings whose lifecycle
is `APPROVED`. Draft, rejected, superseded, and retired relationships cannot
generate reuse candidates.

Accepted evidence can be linked through an assessor-approved reuse decision.
The assessor must still record whether it is fully applicable, partially
applicable, not applicable, or requires additional evidence, including rationale
and scope limitations.

Completed testing can now be referenced from the shared-work workspace when:

- the reuse decision is approved;
- testing reuse is explicitly enabled;
- the source test belongs to the mapped source control; and
- the target objective belongs to the mapped target control.

The reference records limitations and approval provenance. It does not copy the
source control, criterion, or objective conclusion.

## Assessor workflow

1. Select two or more frameworks for an assessment.
2. Open **Harmonize**, analyze approved mappings, and review each candidate.
3. Explicitly approve evidence and/or testing reuse with a rationale.
4. Open **Shared work**.
5. Select appropriate SOC 2 evidence suggestions and create consolidated
   requests.
6. Review each reused artifact for target-specific applicability, timing, and
   scope.
7. Reference prior tests where their population, period, and procedure are
   suitable; document all limitations.
8. Complete each framework's conclusions independently.
