# Increment 1: Identity, Access, and Audit Foundation

## Status

Accepted for implementation. This design completes the security portion of Increment 1 while
retaining Frappe as the authority for users, passwords, sessions, CSRF protection, password
reset, login throttling, and multi-factor authentication.

## Identity boundaries

- `User` remains the login identity. The app will not store passwords, session tokens, OTP
  secrets, or recovery credentials.
- `Staff Profile` adds the college-specific staff number and primary organisational context to a
  system user. It does not replace `User` or duplicate its enabled state.
- Applicant and Student profiles will be introduced with their lifecycle modules. Creating them
  now would produce unused records and premature permissions.
- Frappe `Administrator` is retained as a restricted break-glass account because the framework
  exempts it from ordinary two-factor checks. Daily platform administrators must use named users
  carrying both `System Manager` and the app's `Platform Super Admin` MFA marker role.

## Shipped role templates

| Role | Desk access | Initial purpose |
|---|---:|---|
| Platform Super Admin | Yes | MFA marker for named platform administrators; pair with System Manager |
| Institution Super Admin | Yes | Institution configuration and approved application administration |
| Admissions Officer | Yes | Admissions operations introduced in Increment 2 |
| Registry Officer | Yes | Student and registry operations |
| Finance Officer | Yes | Billing, payment, and reconciliation operations |
| Examination Officer | Yes | Examination review and result processing |
| Academic Approver | Yes | Departmental or institutional academic approval |
| Lecturer | Yes | Assigned teaching and score-entry operations |
| Auditor | Yes | Read-only audit and controlled reporting |
| Student | No | Student portal access |
| Applicant | No | Applicant portal access |

These are safe baseline roles. Institutions may add roles and custom permissions through Frappe.
The role names do not replace per-document, workflow-state, assignment, or ownership checks.
Raw `User` and `Role` administration remains restricted to `System Manager` until the controlled
staff-invitation and role-delegation service is implemented; granting it directly would allow
privilege escalation into framework administration.

## Foundation permission baseline

| Resource | System Manager | Institution Super Admin | Operational staff | Auditor |
|---|---|---|---|---|
| Institution and academic configuration | Full | Full | Read | Read/export |
| Staff Profile | Full | Create/read/update | No default access | Read/export |
| Domain Audit Event | Read/export | Read/export | No access | Read/export |

Student and Applicant receive no Desk permission to foundation configuration. Their later portal
APIs must enforce ownership and publication state on the server.

## MFA and account security

- The `Institution Super Admin` role is marked as requiring Frappe two-factor authentication.
- `System Manager`, `Platform Super Admin`, and `Institution Super Admin` are marked as requiring
  two-factor authentication.
- The production site must enable role-scoped Frappe two-factor authentication with `OTP App` by
  running `bench --site <site> execute college_management.setup.enable_privileged_mfa`. This
  remains an explicit deployment action because running it before enrolling an OTP device can
  lock out an unprepared named administrator.
- Production readiness checks must also confirm password policy, login-attempt limits, password
  reset session revocation, secure cookies, TLS, and removal of development settings.
- Account invitations, activation links, password reset, disabling, and session handling use
  Frappe's maintained `User` lifecycle.

## Audit ledger

`Domain Audit Event` is an append-only application record. It captures foundation configuration
changes with:

- actor and actor roles;
- action and affected document;
- before and after snapshots;
- UTC event time;
- request identifier, IP address, and user agent when a web request supplies them;
- institution and an optional stated reason.

No role receives create, update, or delete permission through Desk. Application hooks write audit
events with explicit permission bypass. The controller rejects ordinary updates and deletion.
Frappe document versions remain enabled as a useful operational history, but they do not replace
the domain ledger.

## Deliberate boundaries

- No custom authentication protocol, token store, cryptography, or session table is introduced.
- Contextual access for assigned courses, owned applications, students, scores, payments, and
  published results will be implemented with those resources, where the scope can be tested.
- Numbering settings will be added together with their first consumers so unused patterns cannot
  drift from the actual naming logic.
- Admission, result, payment, refund, and transcript separation-of-duty rules belong to their
  respective workflows.
