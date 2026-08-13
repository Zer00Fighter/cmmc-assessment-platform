# Omni Web Sprint 5.5

Sprint 5.5 replaces the single-framework assessment assumption with a
backward-compatible primary-plus-many framework architecture.

## Delivered workflow

1. The framework catalog records code, name, version, authority, description,
   effective date, scoring method, maximum score, active state, and requirement
   count.
2. Assessment creation requires one or more frameworks and a selected primary
   framework. Every native requirement from every selection is loaded into the
   same engagement without changing its framework-specific identifier.
3. Existing assessments are migrated automatically: their former framework is
   retained as the selected primary framework and all existing control results,
   evidence, findings, remediation, and exports remain attached.
4. Assessors can add frameworks after creation. Removal is allowed only when
   every result for that framework is untouched. Recorded status, notes,
   ownership, evidence, requests, remediation, or update history blocks removal.
5. The dashboard supports a consolidated view and one filtered view per
   framework. Each framework shows independent completion and, where defined,
   its own numeric score. CMMC uses SPRS with maximum 110; non-scored frameworks
   show progress without inheriting CMMC scoring rules.
6. Explicit requirement crosswalks preserve Equivalent, Partially equivalent,
   and Related mappings between native requirements. Evidence artifacts remain
   reusable across any number of control results and frameworks.
7. The web-bound assessment workbook now includes a Multi-Framework Results
   sheet containing every selected framework, native requirement, result,
   owner, finding, SSP reference, and evidence reference. The existing CMMC
   workbook and Word SSP views remain bound to the primary framework.
8. Framework selection changes and primary-framework changes create tenant
   audit events.

## Current catalog boundary

CMMC Level 2 is currently the only production framework loaded by Omni. The
multi-framework architecture and UI are ready for additional framework import.
The uncommitted CCF mapping workbook remains reserved for the later Omni/CCF
framework-import milestone and is not included in this public repository.

## Public-repository boundary

Framework definitions and public requirements may be committed when their
source and redistribution status are approved. Organization selections,
assessment results, evidence, cross-client mappings, and generated deliverables
remain runtime tenant data and must never be committed.
