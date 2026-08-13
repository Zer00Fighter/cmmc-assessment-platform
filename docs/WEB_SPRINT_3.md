# Omni Web Sprint 3

Sprint 3 connects Omni's curated evidence knowledge and optimized CMMC
documentation-request engine to the authenticated web assessment workflow.

## Delivered workflow

1. Assessors can generate the optimized CMMC request list directly from the
   assessment-procedure workbook. The generated list preserves coverage of all
   110 requirements and is idempotent when generated again.
2. Assessors can also create custom requests or select any framework-agnostic
   canonical object from the Omni Evidence Body of Knowledge.
3. Requests support owner, due date, status, description, and many-to-many
   control mappings. They can be filtered by text, status, domain, and owner.
4. Administrators, Assessors, and Client members can register an uploaded file
   or external reference and link it to multiple requests and controls.
5. Assessors review artifacts as Received, Under review, Accepted, or Rejected.
   Linked request status and dashboard evidence readiness update accordingly.
6. Control assessment pages display their linked supporting artifacts, and the
   dashboard displays artifact counts and accepted-request readiness.

## Evidence security

- Uploaded files are stored below `private_uploads/`, which is ignored by Git.
- There is no public media URL. Downloads pass through an authenticated,
  tenant-scoped view and are returned as attachments.
- File extensions are allow-listed and uploads are limited to 25 MB.
- Cross-tenant access returns HTTP 404 without confirming that an artifact
  exists.
- Request creation/update, artifact creation/update/download, and optimized
  list generation create organization-scoped audit events.
- Client members may submit evidence but cannot set assessor review status or
  assessor notes. Read-only members cannot submit or modify evidence.

Local filesystem storage is appropriate for development. Production hosting
will require encrypted managed object storage, malware scanning, retention and
deletion controls, backup policy, and authorization appropriate to the data
classification of uploaded material.

## Acceptance

The automated web suite covers Sprints 1–3, including curated request creation,
optimized request import, artifact submission, assessor acceptance, dashboard
readiness, and private-file tenant isolation. The real CMMC pipeline produces
271 optimized requests while preserving all 110 control mappings.
