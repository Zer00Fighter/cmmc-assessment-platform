# Sprint 17.8 — CCF Risk Catalog and Governed Control Relationships

Sprint 17.8 adds a canonical CCF risk-definition registry and governed many-to-many relationships between framework controls and possible risks.

- The private CCF Risk Catalog is imported with its exact risk ID, grouping, title, description, source row, filename, and SHA-256.
- Control-to-risk mappings begin as proposed and must be explicitly approved or rejected.
- Omni does not infer control relationships from broad risk groups because the source catalog does not provide control IDs.
- Only approved mappings appear beside assessment findings and contribute to the dashboard's possible-risk exposure list.
- The risk catalog describes possible risks. Organizational likelihood, impact, inherent risk, and residual risk remain separate evaluation decisions.
- Removed catalog entries are deactivated on a later import instead of being silently deleted.

The private workbook is explicitly excluded from the public repository.
