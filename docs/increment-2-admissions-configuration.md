# Increment 2: Admissions Configuration

## Status

Implemented as the first production slice of Increment 2. This configuration is the governed
source for later applicant forms, application submissions, invoices, screening, decisions, and
student conversion.

## Model

### Admission Cycle

An Admission Cycle belongs to an Academic Session and defines the institution-wide application
window and decision deadline. Its lifecycle is:

`Draft → Under Review → Published → Closed → Archived`

Draft authors may return an Under Review cycle to Draft. Publishing requires a System Manager or
Institution Super Admin and at least one enabled Admission Programme. Published configuration is
immutable; corrections require closing the cycle and creating a governed replacement rather than
silently changing rules already presented to applicants.

### Admission Programme

An Admission Programme opens one active Programme, optionally at a Campus, within an Admission
Cycle. It configures capacity, an optional narrower application window, currency, application fee,
whether verified payment will be required before submission, and the programme's application
fields and supporting documents.

The application field catalogue supports Data, Small Text, Date, Select, Check, and Attachment.
Attachment definitions allow only PDF, JPG, JPEG, and PNG and require a 1–25 MB size limit. Actual
uploads will remain private and will be signature-validated when the applicant submission slice is
implemented.

## Permissions and audit

- Institution Super Admin and System Manager can configure and publish cycles.
- Admissions Officer can prepare cycles and programme offerings but cannot publish a cycle.
- Registry Officer and Finance Officer have read access for downstream operations.
- Auditor has read, report, print, and export access.
- Applicant has no generic DocType access; the later portal will expose only explicitly published,
  currently open configuration through a bounded server endpoint.
- Admission Cycle and Admission Programme changes are recorded in Domain Audit Event.

## Deliberate boundaries

This slice does not create applicant accounts, accept submissions or files, issue invoices, or
record decisions. Those records depend on this published configuration and will be added next.
Payment-required is configuration only until server-verified payment transactions exist; no
browser callback will be trusted as payment proof.
