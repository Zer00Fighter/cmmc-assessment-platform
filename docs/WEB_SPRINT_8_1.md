# Omni Web Sprint 8.1

Sprint 8.1 adds business-facing governance and scheduling controls to Sprint 8's
notification engine.

## Governance levels

- The private server setting remains the master SMTP switch.
- Organization Administrators can enable or disable all workflow notifications
  and email delivery from the organization's Notification Governance page.
- Each Assessment Plan can enable or disable notifications and email independently.
- Evidence requests, remediation plans, and remediation milestones include a
  **Notify owner** checkbox for intentional per-action delivery.
- Sign-off and reopening remain mandatory in-app events because they materially
  change the authoritative assessment state.

## Frequency and scheduling

Users can select in-app only, immediate email, daily digest, or weekly digest.
Organization policy controls first and second reminder windows, due-date notices,
initial overdue escalation, and repeat-overdue cadence.

Run reminders daily:

```powershell
.\.venv\Scripts\python.exe manage.py send_workflow_reminders
```

Run digests on the desired schedule:

```powershell
.\.venv\Scripts\python.exe manage.py send_notification_digests
.\.venv\Scripts\python.exe manage.py send_notification_digests --weekly
```

## Escalation recipients

The organization chooses one of these levels:

1. Owner only
2. Owner and Lead Assessor
3. Owner, Lead Assessor, and System Owner

Lead Assessor comes from the Sprint 6 assessment team. The client escalation
email reuses the existing System Owner email on the assessed system. Omni does
not duplicate the client contact in notification settings. If that email is
missing, internal escalation continues without external delivery.

## Email test and security

Organization Administrators can send a safe test message to the email address
on their own Omni account. Tests, reminders, and digests omit evidence contents,
findings, assessor comments, and other sensitive assessment details. SMTP
credentials remain only in the ignored `Omni.local.cmd` file.
