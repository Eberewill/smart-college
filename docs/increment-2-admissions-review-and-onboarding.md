# Increment 2: Admissions Review and Onboarding

## Status and scope

Implemented as the governed lifecycle from a Submitted Admission Application to an Active Student
Profile. It covers configurable review stages, assignments, checklist screening, scoring,
recommendations, final decisions, admission letters, applicant acceptance, and idempotent Registry
conversion. Student enrolment, registration, status-transition actions, and academic history begin
in Increment 3.

## Configuration

Before publishing an Admission Cycle, configure each Admission Programme's ordered Review Stages.
Each stage snapshots:

- a stable stage code and display name;
- the required reviewer role;
- maximum and pass scores; and
- one required document or eligibility check per line.

Optionally select an approved Frappe Print Format whose document type is `Admission Letter`.
Frappe's native print/PDF engine renders the immutable letter record; no separate document engine is
introduced. A custom reviewer role must also receive read access to Admission Review through Role
Permission Manager. Server actions still require the snapshotted role and assignment.

## Authoritative lifecycle

1. Admissions staff call `college_management.admissions.assign_review` for the next configured
   stage and an enabled System User who holds its reviewer role.
2. Only the assigned reviewer calls `college_management.admissions.complete_review`. Every check
   needs a final result. Failed or not-applicable checks need notes; a failed check or below-pass
   score cannot recommend admission.
3. Stages run in configured order. Completed reviews are immutable.
4. After all stages, authorised Admissions staff call `college_management.admissions.record_decision`.
   The decision maker cannot have completed a review for that application. Capacity is locked and
   checked for admitted outcomes. The decision and review summary are immutable.
5. `college_management.admissions.issue_admission_letter` issues one numbered, verifiable letter
   for an admitted decision and snapshots its institution, applicant, programme, session,
   conditions, and approved Print Format.
6. The owning Applicant calls `college_management.admissions.respond_to_admission` once, before the
   deadline, with Accepted or Declined. Late responses become Expired.
7. Registry calls `college_management.admissions.convert_to_student` only for an Accepted letter.
   The action locks the offer, creates one Student Profile, copies the admission identity snapshot,
   and grants the existing Website User the Student role. Retries return the same Student record.

## User interfaces

Applicants use `/admissions`. The portal is available only to signed-in users with the Applicant
role and resolves every record from the current user's Applicant Profile. It provides:

- currently open, published programmes and their application deadlines and fees;
- dynamic application fields from the published programme configuration;
- private attachment upload, draft saving, and controlled submission;
- invoice creation, hosted Paystack checkout, and server-side payment verification when a fee is
  required;
- final decision and reason, admission-letter printing, acceptance or decline, and the assigned
  student number after Registry conversion.

Admissions staff work from the relevant Desk documents. The `Admissions` menu on an Admission
Application opens the review-assignment and final-decision dialogs. Assigned reviewers complete
the configured checklist and scoring from the Admission Review form. Admissions staff issue a
letter from Admission Decision, Registry converts an accepted Admission Letter, and Finance can
reconcile a gateway transaction from Application Payment Transaction. The dialogs call the same
server-governed lifecycle actions described above; they do not bypass permissions or transitions.

## Separation, visibility, and records

- Applicant users never see internal reviews, reviewer comments, or the protected review summary
  on the decision. They can read only their own final outcome/reason, admission letter, and Student
  Profile.
- Admissions Officers assign and decide; assigned reviewers complete their own reviews; Registry
  converts accepted offers. Auditors receive read-only visibility.
- Generic create, write, delete, rename, and status manipulation are not lifecycle controls. The
  whitelisted POST actions validate the actor, state, scope, and input on the server.
- Decisions, issued letter content, completed reviews, and admission identity fields cannot be
  overwritten or deleted. All records participate in the protected domain audit ledger.

## Operator smoke test

1. Add at least one Review Stage to a Draft Admission Programme, then publish its cycle.
2. Sign in as an Applicant, open `/admissions`, save the configured answers, and submit the
   application.
3. Open the submitted Admission Application in Desk and assign its first stage to a staff user with
   the configured role.
4. As that reviewer, complete every check, enter a score, and submit a recommendation.
5. As a different Admissions Officer, record an Admitted decision and issue the letter with a
   future acceptance deadline.
6. As the Applicant, verify that internal reviews are unavailable, then read and accept the letter
   at `/admissions`.
7. As Registry, convert the accepted letter. Confirm one Student Profile exists and the user has the
   Student role. Repeat conversion and confirm the same Student number is returned.

Automated regression command:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management
```
