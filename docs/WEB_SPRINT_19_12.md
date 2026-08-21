# Sprint 19.12 - SOC 2 Reporting and Acceptance Testing

Sprint 19.12 adds a Type I/Type II-aware Word readiness work program and an automated
acceptance gate for the complete SOC 2 workflow.

## Deliverable boundary

The generated document is titled **SOC 2 Readiness Assessment Work Program**. It
documents Omni readiness-assessment work and explicitly states that it is not an AICPA
SOC 2 report, attestation opinion, or substitute for an examination performed
and issued by an independent licensed CPA firm.

## Report content

The Word report includes:

- organization, system, and assessment identity;
- Type I measurement date or Type II examination period;
- included Trust Services categories;
- service commitments and the existing Omni system description/scope;
- executive counts for MET, NOT MET, N/A, and completion;
- in-scope criterion results;
- design and implementation conclusions;
- Type II operating-effectiveness conclusions;
- accepted evidence and approved reused-test references;
- assessor conclusion or finding narratives;
- document request list (DRL), exceptions, and related corrective actions; and
- evidence-period and traceability warnings.

Out-of-scope optional categories do not appear in the criterion table.

## Reporting readiness

Generation is blocked until every in-scope criterion and objective has been
assessed, design and implementation conclusions are recorded, and narrative
support exists. Type II additionally requires an operating-effectiveness
conclusion for every in-scope objective.

The SOC 2 profile does not duplicate a system-boundaries field. The work program
uses the system description and assessment scope already maintained by Omni and
used by other deliverables such as the Security Plan.

Missing accepted evidence, missing evidence dates, incomplete Type II period
coverage, and similar traceability limitations are disclosed as warnings. They
do not silently change criterion conclusions.

The Report Center displays the SOC 2-specific readiness totals, blockers, and
warnings separately from the generic SSP/package readiness checks.

## Acceptance coverage

Automated acceptance tests validate:

- authoritative 61-criterion baseline and category scoping;
- Type I and Type II profile creation;
- service commitments and existing system-description binding;
- objective conclusion requirements;
- rejection of incomplete Type II operating-effectiveness work;
- 33 Security/Common Criteria in the default report scope;
- Word report generation for both examination types;
- the non-CPA-opinion limitation;
- report-center download response and file type;
- generated-document SHA-256 audit metadata; and
- audit-event creation without organization or licensed source data in Git.
