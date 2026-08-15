# Changelog

## Sprint 19.2 — Evidence freshness and renewal

- Added request-level validity periods, renewal lead times, and automatic-renewal policies.
- Added effective dates and policy-derived artifact freshness deadlines.
- Added current, renew-soon, expired, undated, and superseded evidence analytics and filtering.
- Added idempotent manual and scheduled renewal requests with owner notifications and audit history.
- Added renewal lineage and freshness data to the evidence package index and readiness warnings.

## Sprint 19.1 — Assessment templates and integration foundation

- Added organization-scoped assessment templates with recurrence, framework, planning, and evidence-request blueprints.
- Added fresh assessment creation from templates with explicit prior-assessment lineage and no copied conclusions.
- Added a connector-neutral integration policy and outbound work-item synchronization ledger for future Jira and ServiceNow connectors.
- Preserved Omni as the authoritative system for conclusions, evidence acceptance, risk decisions, review, and sign-off.

## Sprint 18.3.1 — Illustrated user manual

- Expanded the Word manual with eight annotated walkthrough figures selected from 16 synthetic screen captures.
- Added an isolated synthetic demonstration-data command for safe, reproducible documentation capture.
- Documented numbered screen callouts for sign-in, setup, planning, execution, evidence, remediation,
  review, reporting, optional risk, framework administration, notifications, and access.
- Corrected assessment-execution rendering when an objective does not yet have an assigned assessor.

## Sprint 18.3 — Comprehensive user and administrator manual

- Added a 14-page, framework-agnostic Word manual for Omni's implemented web application.
- Added an overall assessment-lifecycle diagram and role-based quick-start guidance.
- Documented assessment planning, result entry, evidence, remediation, quality review, reporting,
  multi-framework reuse, optional risk, notifications, framework governance, and administration.
- Added a deterministic public manual builder and preserved the no-client-data repository boundary.

## Sprint 18.2 — Optional risk treatment and continuous monitoring

- Added default-off assessment and reporting toggles for the entire risk capability.
- Added treatment actions, evidence, dependencies, tolerance policies, and residual reassessment.
- Added governed acceptance requests, review, expiration, continuous monitoring, and reminders.
- Added validated closure/reopening and conditional risk-register package export.

## Sprint 18.1 — Guided finding-to-risk workflow

- Added approved catalog-risk suggestions for NOT MET controls.
- Added one-step prefilled risk evaluation from governed relationships.
- Added duplicate control/catalog risk safeguards and registered-state visibility.

## Sprint 18 — Operational risk management

- Added organization-scoped assessment risk registers with control, catalog, owner, and remediation links.
- Added inherent and residual likelihood/impact scoring and true 5×5 risk heatmaps.
- Added mitigate, accept, avoid, and transfer treatment workflows.
- Added administrator-approved, expiring risk acceptance with immutable history.
- Added tenant-scoped risk-register workspace, details, filters, and CSV export.

## Sprint 17.8 — CCF risk catalog and governed control relationships

- Added source-traceable canonical CCF risk definitions and private import tooling.
- Added proposed, approved, and rejected control-to-risk relationship governance.
- Added a superuser-only risk catalog and mapping review workspace.
- Added approved possible-risk exposure to assessment dashboards.
- Explicitly excluded the private CCF Risk Catalog workbook from Git.

## Sprint 17.7 — Framework-weighted risk heatmap

- Added framework-native control weights, including Omni CCF Column F ingestion.
- Shifted CCF mapping discovery to begin naturally after the recognized weighting column.
- Added weighted domain exposure heatmaps for CMMC SPRS and Omni CCF assessments.
- Preserved unassessed weight as unknown exposure rather than treating it as a finding.

## Sprint 17.6 — Authoritative Source Registry

- Added private authoritative-source import, provenance, quality classification, and authority linking.
- Added source registry UI and framework-report citation support.

## Sprint 17.5 — Omni Evidence Catalog integration

- Added source-faithful private Omni evidence-list import and validation.
- Added CMMC L1/L2 alias normalization and canonical evidence curation.
- Added Omni-framework evidence-request generation with governed consolidation.

## Sprint 17 — Mapping governance and change impact

- Added mapping lifecycle, revisions, independent change requests, and immutable history.
- Added impact-driven revalidation tasks and stale draft-report flags.

## Sprint 16 — Multi-framework reporting

- Added framework-specific and consolidated Word assessment reports.
- Added cross-framework traceability CSV export.
- Added reporting profiles, multi-framework readiness, and document approval/version metadata.

## Sprint 15 — Shared evidence and testing workspace

- Added unified mapped-work and remaining-work views.
- Added per-control evidence applicability review and freshness/supersession.
- Added non-destructive evidence-request consolidation.
- Added governed test reuse by reference without copying conclusions.

## Sprint 14 — Omni Control Framework onboarding and mapping curation

- Added an external-authority registry for Omni mapping columns beginning at column F.
- Added a source-faithful mapping-reference ledger with row/column provenance.
- Added superuser-only mapping quality analytics and controlled bulk review.
- Enhanced CCF dry-run reports with authority and mapping-cell counts.
- Preserved immutable framework versions and unresolved references for later catalog resolution.

## Sprint 13 — Multi-framework harmonization and assessment reuse

- Designated the Omni Control Framework as a unique, native mapping hub.
- Added direct and Omni-derived assessment mapping analysis.
- Added governed evidence/testing reuse decisions with reviewer rationale and audit history.
- Reused accepted evidence by reference without propagating compliance outcomes.
- Added harmonization coverage metrics and a tenant-scoped assessment workspace.

## Sprint 12 — Comprehensive Controls Framework ingestion

- Added governed CSV, Excel, and PDF framework ingestion with dry-run previews and explicit approval.
- Added CCF mapping-matrix normalization, preserving source row/page references and cross-framework mappings.
- Added immutable framework-code/version protection, SHA-256 provenance, and mapping approval metadata.
- Added superuser-only ingestion screens and mapping coverage in the framework catalog.

## 1.0.0

- Completed CMMC Level 2 end-to-end acceptance.
- Resolved or explicitly classified all 297 generated evidence requests.
- Established the initial 150-object Evidence Body of Knowledge baseline.
- Added functional Security Plan (SSP) Crosswalk, Assessment History, and
  Executive Report worksheets.
- Added canonical terminology with CMMC display aliases.
- Added atomic workbook saves and timezone-aware assessment timestamps.
- Standardized assessment and scoring package versions at 1.0.0.
