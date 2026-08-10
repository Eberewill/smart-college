# Frappe-Native Applicant Portal Design

## Status

Approved for implementation on 2026-08-10.

## Objective

Finish the applicant portal and standardise it on Frappe's maintained website and portal design
language. The portal must feel native to the installed Frappe release, remain responsive and
accessible, and preserve the existing server-governed admissions lifecycle.

The implementation will not introduce a separate frontend framework or a parallel component
library. Institution-specific presentation is limited to configured identity such as the
institution name, logo, and supported theme colour.

## Routes and information architecture

The applicant experience uses two route types:

- `/admissions` is the applicant dashboard.
- `/admissions/<application-id>` is the owner-protected workspace for one application.

Both routes use Frappe's standard website template, navigation, page container, breadcrumbs, and
portal sidebar. Route handlers resolve the current user's Applicant Profile first and must not
accept a client-supplied applicant identity.

## Admissions dashboard

The dashboard contains a standard page heading, short guidance, and applicant-number metadata.
It has two sections.

### Your Applications

Each application is shown in a simple Frappe card containing:

- programme name;
- application reference;
- a standard status indicator;
- the last-saved or submitted timestamp; and
- one primary `Open application` action.

When no application exists, the section uses a concise native empty state rather than a custom
illustration or promotional panel.

### Available Programmes

Each currently open programme is shown with:

- programme name and code;
- campus when applicable;
- application fee and currency;
- closing date; and
- a primary `Start application` action, or a disabled default action when an application already
  exists.

The cards use the same spacing, headings, borders, and actions as the application cards. The
portal does not introduce a second visual system for programme marketing.

## Application workspace

The workspace header shows the programme name, application reference, and a standard status
indicator. Draft applications render a configured multi-step form.

On large screens, a narrow step list appears to the left of the form content. On smaller screens,
the step list becomes a horizontally scrollable row above the form. The active step uses
`aria-current="step"` and the framework's supported colour and border tokens.

Supported configured step types are:

- Applicant Details;
- Application Fields;
- Payment; and
- Review & Submit.

When a programme has no configured steps, the existing safe default sequence remains available:
applicant details, questions, supporting documents, payment when applicable, and review and
submit.

All data fields use Frappe controls and their native labels, descriptions, required markers,
validation messages, keyboard behaviour, and focus treatment. The portal must not recreate date,
link, select, check, text, or attachment controls when Frappe already supplies the behaviour.

## Saving and navigation

Draft changes autosave through the existing owner-scoped server methods. Step navigation follows
one consistent action hierarchy:

- `Back` uses a default button;
- the save state is announced as muted status text;
- `Save and continue` uses a primary button; and
- `Submit application` appears only in the final review step.

The interface must distinguish saving, saved, and failed states. A failed save remains visible and
must not move the applicant to another step. Submission continues to rely on server-side
completeness, attachment, payment, ownership, and lifecycle validation.

## Attachments and payment

Attachments remain private Frappe File records associated with the owned Admission Application.
The UI shows the configured file restrictions, upload state, existing private document link, and
an actionable error when an upload fails.

Payment presentation uses native cards, alerts, indicators, and buttons. The browser callback is
never treated as proof of payment. The authoritative state remains the server-verified invoice,
transaction, reconciliation, and receipt state.

## Review and submitted views

The final draft step presents a read-only summary of the applicant's profile details, configured
responses, documents, and payment readiness before exposing the submit action.

After submission, editable controls are replaced with a native read-only summary containing:

- submitted answers and owned private document links;
- payment status and receipt state;
- final applicant-visible admission outcome and reason;
- issued admission letter and response action when available; and
- student onboarding status and assigned student number when conversion is complete.

The applicant view never exposes internal reviews, reviewer notes, assignments, protected review
summaries, capacity calculations, audit events, or staff-only workflow controls.

## Design-system rules

The portal will:

- use Frappe's standard website template and supported Bootstrap/Frappe utility classes;
- use framework CSS variables for colour, borders, text, backgrounds, focus, and shadows;
- use native `card`, `alert`, `indicator-pill`, `form-control`, `btn-primary`, and `btn-default`
  conventions where applicable;
- keep custom CSS limited to route-specific layout and responsive step navigation;
- preserve visible keyboard focus, semantic heading order, explicit labels, status announcements,
  and touch-friendly actions; and
- use translatable strings for applicant-visible text.

The portal will not add gradients, decorative hero sections, custom icon sets, animation systems,
oversized marketing panels, or a third-party UI/component dependency.

## Error and empty states

Errors use the framework's normal alert or message presentation and include a recovery action when
one exists. Empty sections explain the actual state without implying an error. Loading and saving
actions disable only the affected control and prevent accidental duplicate submissions.

Owner-scope, permission, or missing-record failures remain server-authoritative and return the
appropriate Frappe error response. Client-side hiding is not an authorisation control.

## Verification and acceptance

Implementation is accepted when:

1. Existing admissions, payment, review, decision, acceptance, and conversion tests remain green.
2. Automated tests cover configured steps, the default sequence, applicant-profile saving,
   owner-scoped route context, and submitted-view visibility.
3. The dashboard and application workspace render without browser console errors.
4. Draft navigation, autosave, attachment, payment, review, and submission paths are exercised in
   the local browser.
5. Desktop and mobile-width layouts retain usable controls, readable content, and visible focus.
6. Ruff and repository diff checks pass.

## Scope boundary

This work finishes the applicant-facing dashboard, application workspace, payment presentation,
submitted summary, admission response, and student-conversion status presentation. It does not
redesign staff Desk screens, change admissions business rules, introduce a frontend framework,
implement later academic-result modules, or create and push the new remote repository.

Repository creation and pushing will be handled as a separate, explicit step after the portal is
implemented, verified, and committed.
