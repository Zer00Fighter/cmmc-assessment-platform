# Sprint 20.2 — Security Hardening

Sprint 20.2 strengthens Omni's application and future deployment boundary while
preserving a practical localhost workflow. Local development is not represented
as production-ready: `security_audit` explicitly reports unresolved deployment
gates until private production settings and infrastructure exist.

## Configuration and secrets

- Production mode rejects the development secret and any secret shorter than 50 characters.
- `OMNI_SECRET_KEY_FALLBACKS` supports a controlled key rotation window without exposing keys in Git.
- Production mode rejects empty or wildcard allowed-host configuration.
- Trusted CSRF origins are explicit through `OMNI_CSRF_TRUSTED_ORIGINS`.
- Forwarded proxy headers are ignored unless `OMNI_TRUST_PROXY_HEADERS=1` is deliberately configured behind a trusted reverse proxy that strips client-supplied forwarding headers.
- No credential value is displayed by the security audit or System Health page.

## Authentication and sessions

- New invitation passwords require at least 12 characters and retain Django's similarity, common-password, and numeric-password validators.
- Login throttling uses the direct network address unless proxy trust is explicitly enabled; arbitrary client `X-Forwarded-For` values cannot evade or redirect the throttle.
- Sessions use Omni-specific cookie names, `HttpOnly`, `SameSite`, a sliding 60-minute timeout, and browser-close expiration.
- Production requires secure session and CSRF cookies, HTTPS redirection, and HSTS.
- Legacy ambiguous signed-cookie salt fallback is disabled.

## Browser and response protections

Omni returns a restrictive Content Security Policy, clickjacking denial,
same-origin resource isolation, permissions restrictions, MIME-sniffing denial,
no-index directives, and unique request identifiers. Authenticated and sensitive
responses receive `no-store`, `private`, and legacy no-cache headers to prevent
browser or intermediary retention of assessment content.

Inline CSS remains permitted solely for Omni's calculated dashboard progress
widths and existing style system. Scripts remain restricted to same-origin
resources; inline scripts, objects, frames, camera, microphone, geolocation,
payment, and USB access are denied.

## Upload defenses

Evidence and framework uploads now enforce more than filename extensions:

- maximum file size and non-empty content;
- PDF, PNG, JPEG, legacy Office, and ZIP-based Office signatures;
- ZIP validity, entry-count and expanded-size limits;
- rejection of encrypted ZIP members that cannot be inspected;
- rejection of null bytes in declared text formats; and
- file-pointer restoration before normal parsing or storage.

These controls reduce malformed and archive-bomb risk. A production pilot still
requires external malware scanning and quarantined object storage before files
are made available to reviewers.

## Audit integrity

The Django administrative interface exposes Omni audit events as read-only.
Administrators cannot add, edit, or delete them through that interface. Normal
application actions continue to append events through governed workflows.

## Dependency security

Sprint 20.2 added the PyPA `pip-audit` scanner and upgraded vulnerable packages:

- Django 5.2.15 → 5.2.17;
- pypdf 6.14.2 → 6.15.0; and
- sqlparse 0.5.5 → 0.6.0.

All resolved direct and transitive packages are pinned in `requirements.txt` so
the audited dependency graph can be reproduced instead of floating to unknown
versions during installation.

Run the combined local check with **Run Omni Security Audit.cmd**, or:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py security_audit
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt --progress-spinner off
```

Use `manage.py security_audit --production` as a release gate. It exits with an
error while any production requirement remains unresolved. Dependency auditing
uses current advisory data and therefore requires network access.

## Deployment boundary

Before public access, Omni still requires Sprint 20.3's controlled deployment
architecture: PostgreSQL, TLS termination, an explicitly trusted proxy,
encrypted private object storage with malware scanning, managed secret storage,
centralized logs/alerts, encrypted off-host backups, and tested rollback.
