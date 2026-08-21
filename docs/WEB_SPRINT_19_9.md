# Sprint 19.9 — SOC 2 Assessment Model

Sprint 19.9 makes the AICPA Trust Services Criteria operational as an Omni
assessment while preserving the platform's framework-neutral core.

## Examination configuration

When the AICPA TSC framework is selected, assessment creation and planning
capture:

- Type I: design assessment as of one required date
- Type II: design and operating effectiveness over a required start/end period
- mandatory Security/Common Criteria scope
- optional Availability, Processing Integrity, Confidentiality, and Privacy
- service commitments, system boundaries, and category-scoping notes

Type I cannot carry a Type II period, Type II cannot carry an as-of date, and
period end cannot precede period start.

## Criterion applicability

Every control result now has an explicit in-scope state and scope rationale.
Saving a SOC 2 profile synchronizes the 61 TSC criteria:

- selected categories are active and begin as `NOT ASSESSED`;
- excluded categories are marked outside scope and `NOT APPLICABLE` with an
  auditable, system-generated rationale;
- adding a previously excluded category clears only the system-generated N/A
  conclusion and returns the criterion to `NOT ASSESSED`;
- manually entered findings or scope decisions are not copied across frameworks.

Control owners continue to use Omni's existing primary and supporting owner
fields. Conformity statements and findings continue to use
`Assessor Notes/Findings`; no duplicate SOC 2-only result fields were created.

## User workflow

1. Create an assessment and select `AICPA-TSC-2017-RPOF-2022` alone or with
   other frameworks.
2. Select Type I or Type II and complete the corresponding date fields.
3. Security is included automatically; select optional categories as needed.
4. Adjust the SOC 2 profile later from **Assessment → Plan**.
5. Assign owners in the existing bulk-owner workspace or on an individual
   criterion.
6. Record criterion conclusions and findings through the normal control-result
   workflow.

The executive dashboard displays the examination type, measurement date or
period, and included Trust Services categories. All scope changes are written to
the assessment audit trail.
