# Sprint 19.6 — Compliance Calendar and Scheduled Workflow Automation

Sprint 19.6 provides one organization calendar for authorized compliance work
and an auditable runner for Omni's existing workflow automation.

## Calendar coverage

- Assessment start and end dates
- Evidence-request deadlines and evidence-freshness dates
- Remediation targets and milestones
- Control-reassessment deadlines
- Optional risk reviews, treatment dates, and acceptance expiration
- Recurring assessment-template dates for organization administrators

Calendar results respect organization membership and assessment-specific access
grants. Filters and CSV exports cannot reveal restricted systems or assessments.

## Automation governance

- Automation is disabled by default for every organization.
- Administrators choose daily or weekly execution and the first run date.
- Each due run is restricted to one organization.
- Every execution records start, finish, status, summary, and error details.
- The runner uses duplicate-safe reminder, renewal, and monitoring workflows.
- Existing notification and assessment email toggles remain authoritative.
- The **Run now** action is administrator-only and always names one organization.

## Windows Task Scheduler

Create one machine-level task that runs daily. Omni's organization policies decide
which organizations are enabled and due; do not create a separate task per client.

1. Open **Task Scheduler** and choose **Create Task**.
2. Use a daily trigger at an operationally appropriate time.
3. Set **Program/script** to `cmd.exe`.
4. Set **Arguments** to `/c "<private-project-path>\Run Omni Automation.cmd"`.
5. Set **Start in** to the private Omni project directory.
6. Run the task once and confirm a successful entry in **Workflow automation**.

The task arguments contain no email password, API key, client name, or evidence
path. Machine-local settings remain in the ignored `Omni.local.cmd` file.

For manual command-line execution:

```powershell
.\.venv\Scripts\python.exe manage.py run_compliance_automation
```

For a controlled administrator test of one organization regardless of its due date:

```powershell
.\.venv\Scripts\python.exe manage.py run_compliance_automation --organization <slug> --force
```

The `--force` option requires an explicit organization slug and cannot trigger a
global manual run.
