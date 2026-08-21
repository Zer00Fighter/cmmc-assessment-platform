# Sprint 20.1 — Data Lifecycle and Recovery

Sprint 20.1 makes local-pilot recovery testable and organization data portable
without publishing, synchronizing, or committing private information.

## Recovery objectives

- Local pilot recovery point objective (RPO): 24 hours.
- Local pilot recovery time objective (RTO): 4 hours after a verified backup is available.
- Default local backup retention: 30 days.
- Recovery rehearsal: quarterly and before each controlled-pilot release.

These are local-pilot objectives, not production commitments. Production RPO,
RTO, encryption, geographic redundancy, and managed PostgreSQL recovery will be
defined with the Sprint 20 deployment architecture.

## Authenticated backups

`backup_omni` creates a transactionally consistent SQLite snapshot and copies
private uploaded files into an ignored ZIP archive. Version 2 manifests record
the path, byte size, and SHA-256 digest of every database and file payload. An
independent SHA-256 sidecar authenticates the complete archive.

```powershell
.\.venv\Scripts\python.exe manage.py backup_omni
.\.venv\Scripts\python.exe manage.py verify_omni_backup local_backups\BACKUP.zip
```

Verification rejects a changed sidecar, corrupt ZIP, unsafe member path,
missing or additional payload, size mismatch, per-file digest mismatch, invalid
manifest, or database that fails SQLite `integrity_check`.

## Non-destructive recovery rehearsal

The staging command verifies the backup before extracting it. It refuses a
non-empty destination and never replaces the active database or evidence root.

```powershell
.\.venv\Scripts\python.exe manage.py stage_omni_restore local_backups\BACKUP.zip
```

The result is written below the ignored `local_restore_staging` directory and
includes `recovery-report.json`. The staged database is opened read-only and
must pass SQLite integrity checking. Do not run Omni from the staging folder.

An approved real recovery remains an offline administrator operation: stop
Omni, preserve the current runtime data, stage and inspect the selected backup,
then replace the resolved runtime targets under a documented change ticket.

## Organization export

Organization Administrators can open **System health** and choose **Export
organization data**. The tenant-scoped ZIP contains:

- a structured organization snapshot;
- systems, assessments, results, workflow and audit records reachable from the organization;
- safe member identity fields, excluding passwords and authentication secrets;
- private files associated with the exported organization; and
- a manifest containing the size and SHA-256 digest of every export member.

Every download creates an `organization.data_exported` audit event. Cross-tenant
records are excluded, and non-administrators receive no export access.

## Retention and deletion

Preview backups older than the configured period:

```powershell
.\.venv\Scripts\python.exe manage.py prune_omni_backups
```

The default is always a dry run. After reviewing the exact list, use
`--confirm` to delete the expired archives and their sidecars. Override the
period only with an approved value, for example `--retention-days 45`.

Confirmed assessment deletion removes its database record and related workflow
data in a transaction. Uploaded evidence files are deleted only after that
transaction commits successfully. The action remains restricted to Organization
Administrators, requires the exact assessment name, and leaves an audit event.

## Privacy boundaries

Backups, restore staging, organization exports, databases, evidence, logs,
credentials, and local configuration are private runtime data. None belong in
the public Git repository. Copy pilot backups off the workstation only through
an approved encrypted storage channel.
