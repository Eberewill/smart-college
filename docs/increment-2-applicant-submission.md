# Increment 2: Applicant Identity and Submission

## Status

Implemented as the applicant transaction layer over published admissions configuration. Applicant
review, payments, decisions, letters, acceptance, and student conversion remain later Increment 2
slices.

## Identity and ownership

- Frappe `User` remains the authentication, email-verification, password-reset, and session
  authority.
- Portal Settings uses `Applicant` as its default signup role when a deployment has not selected a
  different role. Public signup remains controlled by Frappe's signup setting and hourly limit.
- An enabled Website User with the Applicant role receives one `Applicant Profile` automatically.
- Applicant and application numbers use institution-configured naming series.
- Applicant records are owned by their User. Applicant permissions are owner-only; staff access is
  read-only until an explicit review action is introduced.
- User security changes are audited using only enabled state, user type, and role names. Passwords,
  reset keys, OTP data, and session material are never copied to the audit ledger.

## Application lifecycle

This slice implements `Draft → Submitted` through a server-only submission method. Applications
can be created only for enabled programmes in a Published cycle while their effective application
window is open. An applicant may create only their own record and only one application per
programme offering.

Draft responses must match the offering's governed field catalogue. Unknown and duplicate keys,
invalid Select/Check/Date values, text beyond the supported bounds, and files on non-Attachment
fields are rejected. Submission requires every required response and stores an immutable JSON
snapshot of the applicant, offering, and responses.

Submitted applications cannot be edited or deleted. Later review and decision stages will be
separate authorised actions rather than reopening the applicant's submitted record.

## Private supporting documents

An application attachment must:

- be a private Frappe File owned by the applicant;
- be attached to that exact Admission Application;
- use an extension permitted by the published offering;
- remain within the configured 1–25 MB limit; and
- have a PDF, JPEG, or PNG file signature matching its extension.

Production infrastructure must still provide malware scanning. Signature validation reduces type
spoofing but is not an antivirus engine.

## Payment boundary

If an offering requires payment before submission, submission fails closed until the verified
payment slice exists. No browser callback, manually supplied flag, or draft response can represent
payment verification.
