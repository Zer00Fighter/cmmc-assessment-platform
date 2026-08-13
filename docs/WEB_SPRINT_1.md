# Omni Web Sprint 1

Sprint 1 establishes the authenticated, tenant-aware vertical workflow:

> Sign in → select client → select system → open/create assessment → score and
> save a control → see the dashboard update.

## Local setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_cmmc
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. Use Django administration to create the initial
R!SC/client organizations, systems, and organization memberships. An assessor
or organization administrator can then create assessments in the main Omni UI.
After initial setup, Windows users can double-click `Run Omni Web.cmd` to start
the local server and open Omni in their browser.

## Security model

- Every system belongs to one organization.
- Every assessment inherits its tenant from its system.
- Non-superusers see only organizations with an active membership.
- Only Administrator and Assessor memberships can create assessments or edit
  control results; Client and Read-only memberships cannot mutate them.
- Control updates create immutable audit-event records.
- Django CSRF protection, secure password hashing, HttpOnly session cookies,
  clickjacking denial, and content-type sniffing protection are enabled.

SQLite is the local development default. Environment variables allow the same
models to use PostgreSQL later; production secrets and database credentials must
not be committed.

Production mode requires `OMNI_DEBUG=0` and a strong `OMNI_SECRET_KEY`; it also
enables HTTPS redirect, secure session/CSRF cookies, and HSTS. These controls
assume TLS is configured at the application host or trusted reverse proxy.

## Sprint 1 boundaries

The sprint intentionally does not yet include evidence uploads, POA&M screens,
SSP generation from the database, email/password reset delivery, MFA/SSO,
production hosting, or production CUI authorization. Those are subsequent web
sprints.
