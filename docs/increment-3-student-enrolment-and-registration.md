# Increment 3: Student Enrolment and Course Registration

## Status and scope

Implemented as the governed bridge from an Active Student Profile to session enrolment, semester
course registration, controlled student-status changes, and permanent academic history. It uses
the existing Academic Session, Academic Semester, Programme, Academic Level, Curriculum Version,
Course, and prerequisite configuration. Examination scores, grades, GPA/CGPA, progression, and
graduation clearance remain in the next academic-results slice.

## Configuration

Before enrolment:

1. Open the target Academic Session.
2. Configure an Open Academic Semester with registration start/end dates and an add/drop deadline.
3. Activate the applicable Curriculum Version with courses assigned to levels and semester
   numbers, plus any prerequisites.
4. Configure the Programme's minimum and maximum credit load.
5. Review the four student-operation number series on Institution.

Registration fails closed when the semester window, active curriculum, programme credit limits,
or prerequisite evidence is missing.

## Authoritative lifecycle

1. Registry uses the Academics menu on Student Profile to enrol an Active student into one session,
   level, and applicable active curriculum. Repeating the action returns the same enrolment.
2. The owning Student opens `/student`, starts a registration for an open semester, selects only
   courses in the enrolment's curriculum/level/semester, saves a Draft, and submits it.
3. Submission enforces the programme credit range and requires Passed or Exempted academic-history
   evidence for every configured prerequisite.
4. An Academic Approver reviews the registration. A different Academic Approver approves it;
   Administrator is the controlled emergency exception.
5. Before the add/drop deadline, the Student can reopen an Approved registration with a reason,
   edit it, and repeat review and approval.
6. Registry or authorised academic staff locks the final registration. Locked registrations are
   immutable and write one permanent academic-history line per registered course.
7. Registry records status changes through the Student Profile action. Allowed transitions cover
   Active, Deferred, Suspended, Withdrawn, Graduated, and Archived; every transition requires an
   effective date and reason and creates an immutable change and history record.
8. Registry can record verified Passed or Exempted prior-course credit for transfers or migrated
   records. This is the only manual prerequisite evidence until governed examination results are
   implemented.

## Access and records

- Students can read only records linked to their own Student Profile and cannot mutate lifecycle
  fields through generic document writes.
- Registry governs enrolment, status, and prior-credit evidence. Academic Approvers govern review
  and approval. Auditors receive read-only visibility.
- Enrolments, locked registrations, status changes, and academic-history entries cannot be deleted.
- All four record types participate in the domain audit ledger.
- The `/student` portal shows enrolments, open registration opportunities, course selections,
  registration status, add/drop controls, and academic history. Desk exposes the matching staff
  actions and printable Course Registration records.

## Automated regression

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management
```
