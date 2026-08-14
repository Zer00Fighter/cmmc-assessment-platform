# Omni Web Sprint 10

Sprint 10 hardens local operation and prepares Omni for a future controlled
deployment. It does not publish Omni, change DNS, open ports, provision hosting,
or configure `itrisc.com`.

## Local security

- Database-backed login throttling locks a username/source combination after five
  failed attempts for fifteen minutes by default.
- Password recovery uses Django's signed, single-use reset tokens and the configured
  R!SC mailbox. Unknown emails receive the same browser response.
- CSP, permissions policy, same-origin resource/referrer policy, clickjacking,
  MIME-sniffing, secure-cookie, HSTS, and HTTPS settings are centrally configured.
- Evidence uploads retain authenticated download enforcement, a 25 MB application
  limit, a 30 MB request ceiling, allowlisted extensions, and private file permissions.
- Rotating application logs are written under ignored `logs/`. Passwords, tokens,
  evidence contents, findings, and SMTP credentials must never be logged.

## Backup and verification

`backup_omni` creates a transactionally consistent SQLite snapshot plus private
evidence files in `local_backups/`, writes a manifest, and produces an independent
SHA-256 sidecar. `verify_omni_backup` validates the checksum, ZIP members, manifest,
and database payload without overwriting runtime data.

```powershell
.\.venv\Scripts\python.exe manage.py backup_omni
.\.venv\Scripts\python.exe manage.py verify_omni_backup local_backups\BACKUP.zip
```

Restoration is intentionally manual and approval-controlled: stop Omni, verify the
archive, preserve the current database and evidence directory, extract to a separate
staging directory, validate, then replace only the resolved runtime targets. Never
restore directly over a running application.

For future PostgreSQL production, use encrypted provider backups and `pg_dump` /
`pg_restore`; the local SQLite command refuses unsupported engines.

## Scheduled maintenance

Run daily with Windows Task Scheduler while Omni remains local:

```powershell
.\.venv\Scripts\python.exe manage.py run_omni_maintenance
```

It expires invitations, processes reminders, sends daily digests, and creates a
local backup. Run `send_notification_digests --weekly` on the weekly schedule.

## Health and deployment readiness

Organization Administrators can open **System health** to see database status,
email failures, pending invitations, recent audit activity, and future deployment
checks. `manage.py omni_readiness` checks debug mode, secret key, allowed hosts,
HTTPS base URL, PostgreSQL, email, private storage, backup destination, and migrations.

Expected local-only failures such as Debug enabled, HTTP localhost, and SQLite do
not indicate a broken local installation. They are gates to resolve only before a
future deployment at a name such as `omni.itrisc.com`.

## Suggested recovery objectives

- Local pilot RPO: 24 hours, driven by daily backup
- Local pilot RTO: 4 hours after verified backup availability
- Retain 30 daily backups and test a staged restore quarterly
- Keep an encrypted copy outside the workstation before using real client data

No backup, evidence file, database, log, secret, or private configuration belongs
in the public repository.
