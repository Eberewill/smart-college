# Increment 1: Foundation Data Model

## Status

Accepted for implementation. This model belongs to the reusable College Management System app
and assumes one institution per Frappe site and database.

## Relationships

```text
Institution
├── Campus
└── Faculty
    └── Department
        ├── Programme
        └── Course

Academic Session
└── Academic Semester

Academic Level
Course Category

Programme
└── Curriculum Version
    ├── Curriculum Course[]
    │   ├── Course
    │   ├── Academic Level
    │   ├── Semester Number
    │   └── Credit-unit snapshot
    └── Curriculum Prerequisite[]
        ├── Course
        └── Prerequisite Course
```

Campus is a physical-location hierarchy. Faculty and Department form the academic ownership
hierarchy. They are deliberately independent so a faculty is not incorrectly restricted to one
campus. Programme delivery by campus will be modelled later when admissions and programme
offerings are introduced.

## Entities and identity

| Entity | Stable identifier | Important relationships |
|---|---|---|
| Institution | Institution code | One record per site |
| Campus | Campus code | Institution |
| Faculty | Faculty code | Institution |
| Department | Department code | Faculty |
| Academic Session | Session code | Institution-wide period |
| Academic Semester | Session code + semester number | Academic Session |
| Academic Level | Level code | Institution-wide academic progression |
| Course Category | Category code | Institution-wide classification |
| Programme | Programme code | Department |
| Course | Course code | Owning Department and default Course Category |
| Curriculum Version | Curriculum code | Programme and effective sessions |
| Curriculum Course | Child row | Curriculum Version, Course, Level, semester number |
| Curriculum Prerequisite | Child row | Course and prerequisite within one curriculum |

Human-readable codes are immutable after creation. Display names can change without breaking
references, integrations, imports, or historical records.

## Core invariants

1. A configured site contains one Institution record. Application validation gives a clear error
   for a second record, and a database-unique singleton key also prevents concurrent inserts.
2. Codes are normalised to uppercase and cannot be changed after creation.
3. End dates cannot precede start dates.
4. An Academic Semester must fall inside its Academic Session.
5. Semester and registration-window dates must be internally consistent.
6. Programme duration and credit-load limits must be positive and internally consistent.
7. Course credit units must be greater than zero.
8. A Curriculum Version cannot list the same course twice.
9. Curriculum credit units are stored as snapshots and do not silently follow later Course edits.
10. A prerequisite and its target course must both exist in the same Curriculum Version.
11. A course cannot require itself, duplicate a prerequisite, or participate in a prerequisite cycle.
12. Curriculum state transitions follow `Draft → Under Review → Active → Retired`, with a return
    from `Under Review → Draft` allowed.
13. Active and Retired curricula are structurally immutable. Retirement changes status; it does
    not rewrite the curriculum used by historical enrolments or results.

## Deliberate boundaries

- Student, applicant, lecturer, enrollment, course offering, and result records are not part of
  this foundation increment.
- Programme availability by campus belongs to admissions and academic delivery configuration.
- Grading scales and minimum prerequisite grades belong to examination configuration.
- Curriculum assignment to a student will snapshot the Curriculum Version at enrollment.
- Roles and contextual permission rules will be added with the identity and access foundation;
  these configuration DocTypes initially grant full access only to `System Manager`.
