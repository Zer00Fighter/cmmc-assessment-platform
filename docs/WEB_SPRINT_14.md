# Sprint 14 — Omni Control Framework onboarding and mapping curation

Sprint 14 turns the private Omni Control Framework mapping matrix into governed catalog intelligence.

## Private dry run

The source workbook remains private and ignored. A preview records its SHA-256 digest, normalized controls, authority count, source mapping-cell count, validation issues, and row/column provenance without changing the active framework catalog.

## Authority registry and mapping ledger

- Every mapping column beginning at column F becomes an external-authority registry entry.
- Canonical names, aliases, type, issuer, jurisdiction, version, and active status can be curated.
- Every nonempty mapping cell is retained verbatim with its Omni control, workbook row, and workbook column.
- Parsed and resolved references remain separate from the original source text.
- References begin as `RELATED`, `UNRESOLVED`, and `PENDING`; mapping presence never implies equivalence or compliance.

## Governance

Superusers can open **Framework ingestion → Mapping quality**, filter the ledger, and perform controlled approval or rejection. The registry supports later resolution when an external framework is imported, and Sprint 13 consumes only governed catalog relationships for assessment reuse suggestions.

Framework versions are immutable: a new code/version is imported alongside prior versions and never overwrites them.
