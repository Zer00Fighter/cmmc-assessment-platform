# Omni Web Sprint 9

Sprint 9 adds user onboarding, account lifecycle, assessment-specific access,
and auditable access reviews.

## Secure invitations

- Organization Administrators invite a user by email and select the initial role.
- Links use a cryptographically random token. Omni stores only its SHA-256 digest.
- Invitations expire after seven days and are single-use. Administrators can cancel
  pending invitations.
- New users provide their name and password through Omni. Existing email holders
  accept the membership and then authenticate normally.
- Passwords are never emailed or stored in invitation records.

## Organization access lifecycle

Roles remain Administrator, Assessor, Client, and Read Only. Administrators can
activate or deactivate memberships. Omni prevents deactivation of the last active
organization Administrator and warns when a member still owns controls, evidence
requests, remediation plans, or milestones. Historical assessment records retain
their user references after membership deactivation.

## Assessment-specific access

Administrators may grant View Only or Contribute access to an assessment. For
backward compatibility, an assessment with no explicit grants follows organization
membership access. Once at least one grant exists, non-administrators must have an
explicit grant; organization Administrators retain oversight. Assessment lists and
direct dashboard routes enforce the same rule.

## Profiles and access review

Users manage name, email, job title, phone, time zone, notification preferences,
and password. Administrators can export a CSV access-review register containing
role, active state, last login, assessment grants, and outstanding assignment count.
Invitation, membership, grant, profile-related access, and export actions are
covered by tenant boundaries and organization audit events.

## Public-repository boundary

Invitations, token digests, user emails, profiles, access grants, last-login data,
and exports are runtime data. They must never be committed. Automated tests use
synthetic organizations and reserved `.test` email addresses only.
