# Omni Web Sprint 8

Sprint 8 adds tenant-scoped workflow automation, an in-app notification center,
and email-ready delivery. Gmail delivery is disabled by default until an
administrator provides private local configuration.

## Automated workflow events

- Evidence assignments, receipt, status transitions, acceptance, and rejection
- Mandatory assessor comments for rejected evidence and preserved review history
- Objective-level NOT MET findings with a direct finding-to-remediation action
- Remediation ownership, status/validation transitions, and milestone assignments
- Quality-review transitions, changes requested, approval, sign-off, and reopening
- Due-soon and overdue reminders for evidence requests, remediation plans, and
  remediation milestones

Each event records actor, time, affected object, previous/new state, comment,
and notification recipients in workflow history. Existing organization audit
events remain intact.

## Notification center and preferences

Users receive an unread count in Omni's navigation and can open or mark their
own notifications as read. Preferences control in-app-only versus in-app plus
email delivery and opt-in categories for assignments, evidence, remediation,
quality review, and deadlines. Users cannot access another user's notification.

## Gmail configuration

Copy `Omni.local.cmd.example` to the already ignored `Omni.local.cmd`, replace
the example mailbox and password locally, and restart Omni. Use a dedicated
Google Workspace mailbox with two-step verification and an App Password. Never
use or store the mailbox's regular password.

Email messages contain only the organization-independent action summary and a
secure Omni link. Findings, evidence contents, review comments, and other
sensitive assessment details are intentionally excluded.

## Scheduled reminders

Run the following command daily using Windows Task Scheduler or the production
scheduler:

```powershell
.\.venv\Scripts\python.exe manage.py send_workflow_reminders
```

The command is idempotent for the same recipient, item, notification type, and
day. Email failures are recorded on the notification and never roll back the
underlying assessment workflow.

## Public-repository boundary

`Omni.local.cmd`, App Passwords, SMTP credentials, runtime notifications,
organization data, email addresses, and workflow history must never be
committed. The example configuration contains placeholders only. Tests use
synthetic users and reserved `.test` email addresses.
