# Omni Web Sprint 2

Sprint 2 removes the Django administration dependency from normal tenant
onboarding and establishes accountable control ownership.

## Delivered workflow

1. An authenticated user can create an organization and automatically becomes
   its Administrator.
2. Organization Administrators can maintain organization demographics, add and
   edit systems, and assign existing Omni accounts to organization roles.
3. Administrators and Assessors can assign a primary control owner and multiple
   supporting owners while recording an assessment result.
4. Owners can be assigned in bulk to every control in a selected control family.
5. Organization, system, assessment, control-result, and owner operations remain
   tenant-scoped. Sensitive administration screens return no cross-tenant data.

## Roles

- **Administrator:** organization profile, systems, team, assessments, and controls.
- **Assessor:** assessments and controls, including owner assignment.
- **Client:** view access to organization assessment data.
- **Read only:** view access only.

New team members must already have an Omni account. Administrators can locate
them by exact username or email address and assign or update their role.

## Data captured

Organization profiles now include legal name, website, industry, address, and
primary contact information. System profiles include owner contact, location,
environment, hosted data types, system description, CAGE code, and assessment
scope.

The former free-text control-owner value remains in the database for backwards
compatibility with imported workbooks. New web assignments use organization
memberships for validated primary and supporting ownership.
