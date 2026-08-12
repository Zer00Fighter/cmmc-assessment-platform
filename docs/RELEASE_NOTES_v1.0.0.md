# Omni v1.0.0 Release Notes

**Release scope:** CMMC Level 2 workbook workflow  
**Product:** Omni by R!SC

## Release outcome

Omni v1.0.0 is the first feature-complete release of the Excel-delivered CMMC
Level 2 assessment workflow. It retains CMMC-facing terminology while using
framework-independent GRC and Evidence Object concepts internally.

## Included capabilities

- Authoritative CMMC Level 2 control, objective, and scoring data
- Assessment readiness and weighted scoring for all 110 requirements
- Evidence Register and framework-agnostic Evidence Body of Knowledge
- Deterministic DRL generation, optimization, and evidence resolution
- Remediation Action Plan tracking with the CMMC POA&M alias
- Security Plan crosswalk with the CMMC SSP alias
- Live dashboard and domain summaries
- Assessment History live snapshot and manual snapshot register
- Printable live Executive Report with management commentary
- Workbook synchronization, formula restoration, and automatic recalculation
- Atomic workbook saves that do not expose a partially written release file

## Acceptance baseline

- 297 generated evidence requests
- 0 unresolved titles
- 100% classified requests
- 98.32% collectible-evidence coverage
- 110 CMMC Level 2 requirements
- 297 assessment objectives

The permanent real-data coverage gate fails if an unresolved generated title is
introduced.

## Terminology model

| Canonical Omni term | CMMC display alias |
|---|---|
| Security Plan | System Security Plan (SSP) |
| Remediation Action Plan | POA&M |
| Requirement | CMMC Practice / Requirement |
| Assessment Objective | CMMC Assessment Objective |

Aliases preserve framework familiarity without creating duplicate platform
objects.

## Framework boundary

The Evidence Body of Knowledge, request architecture, and resolution model are
framework-independent. The current compiler, scoring package, source data, and
workbook presentation are intentionally CMMC-specific release adapters. A new
framework should add its own adapter and mappings rather than embedding its
terminology in shared evidence components.

## Known boundaries

- The deliverable is an Excel workbook, not yet a hosted multi-tenant service.
- Historical snapshots are preserved by copying the live history row and
  pasting it as values into the register; the workbook contains no macros.
- Formula values are recalculated by Excel or a compatible spreadsheet engine
  when the workbook opens.
- Additional frameworks may reveal new legitimate Evidence Objects or aliases;
  these should use the governed evidence-curation process.

## Next roadmap boundary

Roadmap milestones 12–20—beginning with ingestion of a second control
framework—are intentionally deferred until a later phase.
