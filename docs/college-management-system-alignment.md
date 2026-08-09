# College Management System

## Product, Architecture, and Delivery Alignment

**Product owner:** Willex Tech  
**Initial deployment:** Muwanshat College of Health Science and Technology, Jalingo, Taraba State  
**Document type:** Binding architecture and delivery decision record  
**Status:** Accepted  
**Date:** 9 August 2026  
**Applies to:** `project (1).md`, College Management System Project Definition and Engineering Blueprint

---

## 1. Purpose

This document records the decisions made after reviewing the College Management System requirements against Frappe Framework. It aligns the product definition, deployment model, technical architecture, security approach, and delivery expectations before implementation begins.

The original requirements remain in force except where this document explicitly replaces or clarifies them. In the event of a conflict, this alignment document governs until the requirements are consolidated into the custom application's permanent documentation.

## 2. Product Commitment

The system is a production-grade College Management System. It is not an MVP, prototype, proof of concept, or disposable demonstration.

The complete agreed product scope includes:

- Applicant registration, applications, document submission, screening, admission decisions, and onboarding
- Student records, programme enrolment, curriculum management, course registration, and academic standing
- Lecturer allocation, continuous-assessment and examination score entry, review, approval, locking, and amendment
- GPA, CGPA, carryover, graduation evaluation, result publication, statements of result, and transcripts
- Fee configuration, invoices, verified online payments, reconciliation, receipts, adjustments, waivers, and refunds
- Staff, applicant, student, finance, examination, registry, audit, and administrative interfaces
- Configurable institutional rules, templates, numbering, workflows, permissions, notifications, and reports
- Security, auditability, testing, backup, monitoring, recovery, deployment automation, documentation, and operational readiness

Delivery may occur in controlled phases, but phasing does not redefine the product as an MVP or lower the production standard. A phase is complete only when its included features meet the project's Definition of Done.

## 3. Commercial and Deployment Model

### 3.1 One reusable product codebase

Willex Tech will own and maintain one reusable College Management System application source codebase. The codebase may be licensed, configured, and deployed for multiple institutions without creating institution-specific forks.

Institution-specific differences must be expressed through validated configuration, master data, templates, permissions, feature activation, and versioned policies. Institution names, programmes, fees, grades, document layouts, approval chains, and similar rules must not be hard-coded.

### 3.2 Single-tenant deployments

The product is not a shared-database, shared-site multitenant SaaS platform.

Each customer institution receives an isolated deployment consisting of its own:

- Frappe site
- Database
- Site configuration and encryption key
- Private and public files
- Domain and TLS configuration
- Integration credentials
- Queues, scheduled jobs, backups, and monitoring context
- Development, staging, and production environments as contracted

Deployments use the same versioned application source code but do not share institutional data. This isolation is the primary institutional boundary.

### 3.3 Consequences of this decision

- Institution identifiers are not required on every business record solely for tenant filtering.
- Cross-institution queries and administration are outside the application site's normal operation.
- A failure in one institution's permission filter cannot expose another institution's database because the institutions are not stored in the same site.
- Releases and migrations must be repeatable across separately deployed customer sites.
- Backups, restores, retention policies, secrets, and integrations are managed per deployment.
- Any future fleet-management or licensing console must be a separate, explicitly designed control-plane product. It must not create direct access to institutional records by default.

## 4. Technical Foundation

### 4.1 Framework decision

The system will be implemented as a separate custom Frappe application. Frappe Framework provides the application runtime and common platform capabilities; the College Management System app provides the education-specific domain model, rules, workflows, interfaces, reports, and integrations.

The application must not be implemented through direct changes to Frappe core. Framework changes may only be considered when no supported extension mechanism exists, the change is independently reviewed, upgrade implications are documented, and an upstream contribution or maintainable compatibility strategy is approved.

### 4.2 Production stack

The initial production architecture is:

- **Application framework:** A supported stable Frappe Framework release
- **Domain application:** Willex Tech College Management System custom Frappe app
- **Backend:** Python services, DocTypes, controllers, hooks, permission rules, whitelisted methods, and scheduled/background jobs within Frappe
- **Staff interface:** Frappe Desk with purpose-built workspaces, forms, reports, dashboards, and custom pages where needed
- **Applicant, student, and lecturer experience:** Responsive Frappe web/portal interfaces, with custom frontend components where the standard interface is insufficient
- **API:** Versioned application endpoints implemented through Frappe; automatic generic resource APIs are not the sole contract for sensitive workflows
- **Database:** MariaDB as the initial supported production database unless deployment validation approves PostgreSQL
- **Queue and cache:** Redis through the Frappe/Bench process model
- **Files:** Private Frappe file handling with production object storage where required
- **Documents:** Server-generated, versioned print formats and PDFs
- **Edge:** TLS reverse proxy, secure headers, request limits, and infrastructure-level protection
- **Operations:** Bench-compatible deployment automation, workers, scheduler, monitoring, encrypted backups, restore procedures, and rollback capability

### 4.3 Deferred architectural components

FastAPI, Go microservices, React/Next.js as a separate primary frontend, and service extraction are not part of the initial architecture. They may be introduced only when a documented requirement cannot be met responsibly through Frappe or when measured scale and operational evidence justify the added complexity.

A separate frontend, if later approved, must use the same server-side Frappe permissions and domain services. It must not duplicate authentication, academic calculations, payment verification, or authorisation logic in the browser.

## 5. Frappe Capability Boundary

### 5.1 Platform capabilities to use

The application will use supported Frappe capabilities for:

- DocTypes, database migrations, naming series, and document lifecycle
- Users, roles, role profiles, permissions, user permissions, and contextual permission hooks
- Workflows, assignments, notifications, email, background jobs, and scheduling
- Forms, lists, workspaces, dashboards, reports, exports, Print Formats, and PDFs
- REST/RPC transport, secure server-managed sessions, CSRF protection, and request handling
- File records, private file access, comments, communications, and standard document version tracking
- Site configuration, encrypted password fields, logging, caching, and queues

### 5.2 College-specific capabilities to build

The custom application is responsible for:

- Configurable admission cycles, programme requirements, screening, admission decisions, and student conversion
- Academic structure, curriculum versions, course offerings, prerequisites, credit limits, and registration windows
- Lecturer-course allocation and context-sensitive access to class lists and scores
- Score components, bulk imports, validation, submission, review, approval, locking, publication, and amendment
- Version-aware GPA, CGPA, carryover, probation, graduation, and academic-standing calculations
- Fee rules, invoice generation, gateway adapters, signed webhooks, verification, idempotency, reconciliation, waivers, adjustments, and refunds
- Result broadsheets, statements, transcripts, verification identifiers, and QR verification
- Domain audit events, separation-of-duty checks, sensitive-operation reasons, and controlled publication
- Applicant, student, and lecturer portal journeys
- Institution-specific configuration validation, versioning, effective dating, publication, and rollback

### 5.3 Infrastructure and operational controls

The following are deployment responsibilities and must not be treated as application-form settings alone:

- TLS, firewall rules, WAF or edge rate limiting, and exposed-port policy
- Secret management and credential rotation
- Malware scanning for uploaded files where required
- Object-storage encryption and access policies
- Centralised logs, metrics, alerts, uptime monitoring, and certificate monitoring
- Encrypted backups, off-site backup copies, restoration exercises, and disaster recovery
- Operating-system, database, Redis, reverse-proxy, and dependency patching
- Production access procedures and environment separation

## 6. Identity and Authentication Alignment

The system will use Frappe's maintained authentication and server-side session facilities rather than implement password hashing, cookies, CSRF, session identifiers, or cryptography independently.

The security outcome remains binding:

- Secure server-managed sessions
- Secure, `HttpOnly`, and appropriate `SameSite` cookies in production
- MFA for privileged administrative roles
- Configured password length and login-attempt controls
- Session revocation following suspension, password reset, or privilege removal where required
- Generic account-recovery responses and rate-limited authentication endpoints
- Re-authentication or an approved equivalent control for high-risk actions
- Authentication and privilege-change audit events

The original requirement mandating Argon2id specifically is replaced by the requirement to use a reviewed adaptive password-hashing implementation supported by the selected stable Frappe release. If a customer or compliance assessment requires a particular hashing algorithm or external identity standard, that requirement will be met through an approved identity-provider integration or a separately reviewed compatibility design—not an undocumented Frappe core patch.

## 7. Authorisation and Separation of Duties

Every sensitive operation must be authorised on the server. Hiding a button, field, route, report, or navigation item is not an authorisation control.

The permission design combines:

- Frappe role and DocType permissions for broad capability
- User permissions for organisational restrictions where suitable
- Permission query conditions for scoped lists and reports
- Per-document permission hooks for ownership, assignment, department, programme, course, and state rules
- Explicit checks within domain services for actions such as approve, publish, reverse, amend, export, and issue
- Workflow transition rules for state-dependent authority
- Separation-of-duty checks that compare the current actor with prior initiators or approvers

High-impact operations must never rely on the unrestricted generic resource API without the same domain checks used by the interface.

## 8. Academic and Financial Record Integrity

### 8.1 Versioned configuration

Curricula, grading scales, assessment structures, fee schedules, graduation requirements, and document templates must have effective dates or explicit versions. Published historical records must retain references to the versions used when they were calculated or issued.

Changing a current configuration must not silently change:

- Previously published results
- Historical GPA or CGPA
- Verified payments or issued receipts
- Approved course registrations
- Issued statements or transcripts
- Prior admission decisions

### 8.2 Explicit publication

Draft, submitted, approved, locked, and published are distinct states. Approval does not automatically imply publication unless an approved institutional workflow explicitly combines them.

Only published results are visible to students. Only issued documents are treated as official documents.

### 8.3 Amendments instead of destructive edits

Post-publication changes must use linked amendment records. An amendment records the original value, proposed value, reason, requester, reviewers, approvers, timestamps, and resulting publication. It must not erase the original record.

Verified payment transactions are immutable. Refunds, reversals, waivers, and adjustments are separate linked records with their own permissions and approvals.

## 9. Audit Architecture

Frappe document version tracking will be enabled where useful, but it is not the complete audit solution.

The custom application will maintain a protected domain audit ledger for required events, including:

- Actor, role, action, resource, and document identifier
- Previous and resulting state or values where appropriate
- UTC timestamp and institutional display timezone
- Request or correlation identifier
- Source IP and user-agent information where lawful and useful
- Institution deployment identifier
- Reason for amendments or other sensitive actions
- Related workflow, payment, result, transcript, export, or configuration reference

Ordinary application users must not be able to edit or delete audit events. Audit access and export are themselves audited. Infrastructure log retention and tamper resistance complement, but do not replace, the domain ledger.

## 10. Configurability Boundary

Configuration is preferred over institution-specific code, but every configuration option must have a clear supported domain meaning.

The initial admissions configuration will support a governed catalogue of fields and documents whose label, help text, visibility, requirement status, order, and programme applicability can be configured. A completely arbitrary runtime form builder is not implied unless it is separately specified and accepted.

Critical configuration follows draft, review, publish, effective-date, and supersession rules as appropriate. Rollback creates a new governed version or restores a prior version through an audited action; it does not erase intervening history.

Feature flags control the availability of complete, tested modules. They must not expose unfinished production functionality or bypass permissions.

## 11. User Experience Strategy

The staff experience will use Frappe Desk where it provides an efficient and accessible operational interface. Custom Desk pages will be created for high-volume or specialised tasks such as score sheets, result broadsheets, reconciliation, bulk imports, and controlled publication.

Applicant and student journeys must be designed as focused responsive portal experiences rather than exposing the administrative Desk. Lecturer workflows may use Desk or a purpose-built portal depending on usability and device requirements.

All interfaces remain subject to server-side validation, permissions, workflow rules, pagination, bounded exports, accessibility checks, and mobile-browser testing.

## 12. Delivery Model

Implementation will proceed through production-quality increments so that domain and security risks are resolved in dependency order. These increments are not throwaway prototypes and do not reduce the committed product scope.

### Increment 1: Foundation and institutional configuration

- Stable Frappe/Bench environment and custom app
- Development, test, staging, and production deployment design
- Institution profile, branding, organisation, academic calendar, and numbering
- Identity, roles, permissions, MFA, audit foundation, and security baseline
- Versioned configuration patterns and shared document services

### Increment 2: Admissions and applicant finance

- Applicant accounts, verification, application forms, uploads, and submission
- Admission cycles, screening, decisions, communications, and admission letters
- Application invoices, gateway integration, verification, reconciliation, and receipts
- Admission acceptance and controlled conversion to student records

### Increment 3: Student and academic operations

- Students, programmes, curricula, sessions, semesters, levels, and course offerings
- Enrollment, course availability, registration, prerequisite and credit validation
- Registration review, approval, locking, add/drop rules, and printable forms
- Lecturer allocation, class lists, attendance where agreed, and student portal records

### Increment 4: Examinations and results

- Assessment structures, score entry, approved bulk templates, and validation
- Submission, return, review, approval, locking, and publication
- GPA, CGPA, carryover, probation, academic standing, and graduation evaluation
- Broadsheets, statements, amendments, republication, and complete domain audits

### Increment 5: Student finance, transcripts, and reporting

- Fee schedules, student invoices, payments, reconciliation, waivers, adjustments, and refunds
- Transcript requests, preparation, approval, issuance, and verification
- Operational dashboards, reports, governed exports, notifications, and templates
- Administrative configuration and operational visibility

### Increment 6: Production hardening and launch

- Migration rehearsal and validation
- Functional, authorisation, integration, end-to-end, security, accessibility, and load testing
- Backup restoration and deployment rollback demonstration
- Monitoring, alerting, incident procedures, operations documentation, and staff training
- Vulnerability remediation, user acceptance, and formal production approval

An increment may be exercised in development or staging before the entire product is complete. No such environment or partial increment may be represented as the finished production system.

## 13. Quality and Release Policy

The original Definition of Done, testing requirements, secure-development lifecycle, and go-live acceptance criteria remain binding.

Additionally:

- The application must pin a supported stable Frappe release; the framework `develop` branch is not a production dependency.
- Framework upgrades must be tested against migrations, permissions, workflows, calculations, portals, reports, payments, and documents before customer deployment.
- Domain calculations must be deterministic and covered by automated tests using known academic examples.
- Authorisation tests must include list access, individual document access, reports, exports, files, APIs, and background jobs.
- Payment tests must include duplicate, delayed, replayed, invalidly signed, out-of-order, and manually reconciled events.
- Production releases require versioned migrations, release notes, rollback planning, and database/file backup verification.
- No critical or high-severity security finding may remain unresolved at go-live.

## 14. Repository and Ownership Model

The intended structure is:

```text
frappe-bench/
├── apps/
│   ├── frappe/                 # pinned framework dependency
│   └── college_management/     # Willex Tech product source
├── sites/
│   ├── development site
│   └── customer site configuration (not committed)
└── deployment configuration
```

The `college_management` repository will contain:

- Domain modules and DocTypes
- Server-side services and permission policies
- Portal and Desk interfaces
- Reports, print formats, notifications, and fixtures
- Automated tests and test data builders
- Migrations and patches
- Architecture decisions, security guidance, deployment documentation, and operational runbooks

Secrets, customer databases, generated private files, production data, and environment-specific credentials must never be committed.

## 15. Decisions That Supersede the Original Blueprint

| Original area | Accepted decision |
|---|---|
| Recommended React/Next.js frontend | Frappe Desk and Frappe portal first; separate frontend only through an approved later decision |
| Recommended FastAPI or Go backend | Frappe/Python custom application |
| Generic modular-monolith service interfaces | Domain modules inside the custom Frappe app, with shared rules exposed through explicit Python services |
| PostgreSQL as recommended database | MariaDB initially; PostgreSQL only after full deployment validation |
| Tenant-aware shared data model | Isolated Frappe site and database per institution |
| Institution identifier on every record | Not required solely for tenancy; include organisational links only where they have domain meaning |
| Platform Super Admin inside an institution site | Institution administration only; any future platform control plane is a separate product |
| Mandatory Argon2id implementation | Supported adaptive hashing through Frappe or an approved external identity provider |
| Six phases described as general delivery | Production-quality increments with the full product scope and Definition of Done preserved |

## 16. Outstanding Discovery Decisions

The following inputs are required before their affected modules can be finalised. They are discovery dependencies, not optional product scope:

- Institution organisation, programmes, levels, course catalogue, and curriculum versions
- Academic calendar and enrollment rules
- Grading, GPA/CGPA, carryover, probation, and graduation rules with worked examples
- Admission application, supporting documents, review stages, and decision authority
- Fee schedules, waivers, refunds, gateway choice, settlement process, and reconciliation ownership
- Admission letter, receipt, registration form, statement, broadsheet, and transcript samples
- Required operational and statutory reports
- Role and permission matrix, separation-of-duty rules, and authorised representatives
- Existing data sources, quality, mapping rules, volumes, and migration acceptance method
- Hosting, availability, recovery objectives, retention policy, support model, and budget
- Branding, domains, email, SMS, and notification requirements

## 17. Final Direction

Willex Tech will build a reusable, configurable, production-grade College Management System as a custom application on a supported stable Frappe release. Each institution will receive an isolated single-tenant deployment using the same maintained product source code.

The project will favour Frappe's maintained platform capabilities, implement college-specific rules in the custom app, preserve immutable academic and financial history, enforce all sensitive rules on the server, and treat security, testing, deployment, recovery, documentation, and operational readiness as part of the product rather than post-development additions.
