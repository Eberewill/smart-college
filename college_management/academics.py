import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

REGISTRY_ROLES = {"System Manager", "Institution Super Admin", "Registry Officer"}
ACADEMIC_ROLES = {"System Manager", "Institution Super Admin", "Academic Approver"}
STAFF_READ_ROLES = REGISTRY_ROLES | ACADEMIC_ROLES | {"Examination Officer", "Auditor"}


def student_record_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	ptype = ptype or "read"
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or STAFF_READ_ROLES.intersection(roles):
		return ptype in {"read", "print", "report", "export"}
	student = frappe.db.get_value("Student Profile", doc.student, ["user"], as_dict=True)
	return bool(student and ptype in {"read", "print"} and student.user == user)


@frappe.whitelist(methods=["POST"])
def enrol_student(student, academic_session, academic_level, curriculum_version=None):
	_require_role(REGISTRY_ROLES, "Only Registry can enrol a student.")
	_lock("Student Profile", student)
	profile = frappe.get_doc("Student Profile", student)
	if profile.status != "Active":
		frappe.throw(frappe._("Only an Active student can be enrolled."))
	if not frappe.db.get_value("Academic Level", academic_level, "is_active"):
		frappe.throw(frappe._("Select an active Academic Level."))
	existing = frappe.db.get_value(
		"Student Enrolment", {"student": student, "academic_session": academic_session}, "name"
	)
	if existing:
		return {"enrolment": existing, "status": frappe.db.get_value("Student Enrolment", existing, "status")}
	session = frappe.get_doc("Academic Session", academic_session)
	if session.status in {"Closed", "Archived"}:
		frappe.throw(frappe._("Students cannot be enrolled into a closed Academic Session."))
	curriculum = _curriculum(profile.programme, session, curriculum_version)
	enrolment = frappe.get_doc(
		{
			"doctype": "Student Enrolment",
			"student": student,
			"programme": profile.programme,
			"department": profile.department,
			"campus": profile.campus,
			"academic_session": session.name,
			"academic_level": academic_level,
			"curriculum_version": curriculum.name,
			"status": "Active",
			"enrolled_on": nowdate(),
			"enrolled_by": frappe.session.user,
		}
	)
	enrolment.owner = profile.user
	enrolment.flags.academic_action = True
	enrolment.insert(ignore_permissions=True)
	profile.current_level = academic_level
	profile.flags.registry_action = True
	profile.save(ignore_permissions=True)
	_history(enrolment, "Enrolment", outcome="Active", details=f"Enrolled in {session.session_name}")
	return {"enrolment": enrolment.name, "status": enrolment.status}


@frappe.whitelist(methods=["POST"])
def create_course_registration(enrolment, academic_semester):
	_lock("Student Enrolment", enrolment)
	enrolment_doc = frappe.get_doc("Student Enrolment", enrolment)
	_require_student(enrolment_doc.student)
	if enrolment_doc.status != "Active":
		frappe.throw(frappe._("Course registration requires an Active enrolment."))
	semester = frappe.get_doc("Academic Semester", academic_semester)
	if semester.academic_session != enrolment_doc.academic_session:
		frappe.throw(frappe._("The semester must belong to the enrolment's Academic Session."))
	_validate_registration_window(semester)
	existing = frappe.db.get_value(
		"Course Registration",
		{"student": enrolment_doc.student, "academic_semester": semester.name},
		"name",
	)
	if existing:
		return {
			"registration": existing,
			"status": frappe.db.get_value("Course Registration", existing, "status"),
		}
	profile = frappe.get_doc("Student Profile", enrolment_doc.student)
	registration = frappe.get_doc(
		{
			"doctype": "Course Registration",
			"student": profile.name,
			"student_enrolment": enrolment_doc.name,
			"programme": enrolment_doc.programme,
			"academic_session": enrolment_doc.academic_session,
			"academic_semester": semester.name,
			"academic_level": enrolment_doc.academic_level,
			"curriculum_version": enrolment_doc.curriculum_version,
		}
	)
	registration.owner = profile.user
	registration.flags.academic_action = True
	registration.insert(ignore_permissions=True)
	return {"registration": registration.name, "status": registration.status}


@frappe.whitelist(methods=["POST"])
def save_course_registration(registration, courses):
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	_require_student(doc.student)
	if doc.status != "Draft":
		frappe.throw(frappe._("Only a Draft course registration can be edited."))
	_validate_registration_window(frappe.get_doc("Academic Semester", doc.academic_semester), add_drop=True)
	selected = frappe.parse_json(courses) if isinstance(courses, str) else courses
	if not isinstance(selected, list) or len(selected) != len(set(selected)):
		frappe.throw(frappe._("Select each course once."))
	available = _available_courses(doc)
	if not set(selected).issubset(available):
		frappe.throw(frappe._("Every selected course must belong to this curriculum, level, and semester."))
	doc.set("courses", [])
	for course in selected:
		row = available[course]
		doc.append(
			"courses",
			{
				"course": course,
				"course_title": row.course_title,
				"course_category": row.course_category,
				"credit_units": row.credit_units,
			},
		)
	doc.total_credit_units = sum(flt(row.credit_units) for row in doc.courses)
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	return {"registration": doc.name, "status": doc.status, "total_credit_units": doc.total_credit_units}


@frappe.whitelist(methods=["POST"])
def submit_course_registration(registration):
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	_require_student(doc.student)
	if doc.status != "Draft":
		frappe.throw(frappe._("Only a Draft course registration can be submitted."))
	_validate_registration_window(frappe.get_doc("Academic Semester", doc.academic_semester), add_drop=True)
	_validate_registration(doc)
	doc.status = "Submitted"
	doc.submitted_at = now_datetime()
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	return {"registration": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def review_course_registration(registration, notes=None):
	_require_role(ACADEMIC_ROLES, "Only an Academic Approver can review course registrations.")
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	if doc.status != "Submitted":
		frappe.throw(frappe._("Only a Submitted course registration can be reviewed."))
	_validate_registration(doc)
	doc.status = "Reviewed"
	doc.reviewed_by = frappe.session.user
	doc.reviewed_at = now_datetime()
	doc.review_notes = (notes or "").strip()
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	return {"registration": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def approve_course_registration(registration):
	_require_role(ACADEMIC_ROLES, "Only an Academic Approver can approve course registrations.")
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	if doc.status != "Reviewed":
		frappe.throw(frappe._("Only a Reviewed course registration can be approved."))
	if frappe.session.user != "Administrator" and doc.reviewed_by == frappe.session.user:
		frappe.throw(frappe._("The reviewer and approver must be different users."), frappe.PermissionError)
	doc.status = "Approved"
	doc.approved_by = frappe.session.user
	doc.approved_at = now_datetime()
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	return {"registration": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def reopen_course_registration(registration, reason):
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	_require_student(doc.student)
	if doc.status != "Approved" or not (reason or "").strip():
		frappe.throw(frappe._("An approved registration and a reason are required for add/drop."))
	_validate_registration_window(frappe.get_doc("Academic Semester", doc.academic_semester), add_drop=True)
	doc.status = "Draft"
	doc.reviewed_by = doc.reviewed_at = doc.approved_by = doc.approved_at = None
	doc.review_notes = frappe._("Add/drop requested: {0}").format(reason.strip())
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	_history(doc, "Registration Reopened", details=reason.strip())
	return {"registration": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def lock_course_registration(registration):
	_require_role(ACADEMIC_ROLES | REGISTRY_ROLES, "Only authorised academic staff can lock registrations.")
	_lock("Course Registration", registration)
	doc = frappe.get_doc("Course Registration", registration)
	if doc.status != "Approved":
		frappe.throw(frappe._("Only an Approved course registration can be locked."))
	doc.status = "Locked"
	doc.locked_by = frappe.session.user
	doc.locked_at = now_datetime()
	doc.flags.academic_action = True
	doc.save(ignore_permissions=True)
	for row in doc.courses:
		_history(
			doc,
			"Course Registration",
			course=row.course,
			credit_units=row.credit_units,
			outcome="Registered",
		)
	return {"registration": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def change_student_status(student, status, effective_date, reason):
	_require_role(REGISTRY_ROLES, "Only Registry can change student status.")
	_lock("Student Profile", student)
	profile = frappe.get_doc("Student Profile", student)
	allowed = {
		"Active": {"Deferred", "Suspended", "Withdrawn", "Graduated", "Archived"},
		"Deferred": {"Active", "Withdrawn", "Archived"},
		"Suspended": {"Active", "Withdrawn", "Archived"},
		"Withdrawn": {"Archived"},
		"Graduated": {"Archived"},
		"Archived": set(),
	}
	if (
		status not in allowed.get(profile.status, set())
		or not (reason or "").strip()
		or not effective_date
		or not (getdate(profile.admission_date) <= getdate(effective_date) <= getdate(nowdate()))
	):
		frappe.throw(frappe._("This student status transition is not allowed or has no reason."))
	change = frappe.get_doc(
		{
			"doctype": "Student Status Change",
			"student": profile.name,
			"from_status": profile.status,
			"to_status": status,
			"effective_date": effective_date,
			"reason": reason.strip(),
			"approved_by": frappe.session.user,
			"approved_at": now_datetime(),
		}
	)
	change.owner = profile.user
	change.flags.academic_action = True
	change.insert(ignore_permissions=True)
	profile.status = status
	profile.flags.registry_action = True
	profile.save(ignore_permissions=True)
	_history(change, "Student Status", outcome=status, details=reason.strip())
	return {"change": change.name, "student": profile.name, "status": status}


@frappe.whitelist(methods=["POST"])
def record_prior_course(student, course, outcome, effective_date, reason, academic_session=None):
	_require_role(REGISTRY_ROLES, "Only Registry can record prior academic history.")
	profile = frappe.get_doc("Student Profile", student)
	if (
		outcome not in {"Passed", "Exempted"}
		or not (reason or "").strip()
		or not effective_date
		or getdate(effective_date) > getdate(nowdate())
	):
		frappe.throw(frappe._("Prior credit requires Passed or Exempted and a reason."))
	return {
		"history": _history(
			profile,
			"Prior Course Credit",
			course=course,
			credit_units=frappe.db.get_value("Course", course, "default_credit_units"),
			outcome=outcome,
			details=reason.strip(),
			effective_date=effective_date,
			academic_session=academic_session,
		).name
	}


def _validate_registration(doc):
	if not doc.courses:
		frappe.throw(frappe._("Select at least one course."))
	minimum, maximum = frappe.db.get_value(
		"Programme", doc.programme, ["minimum_credit_load", "maximum_credit_load"]
	)
	total = sum(flt(row.credit_units) for row in doc.courses)
	if total < flt(minimum) or total > flt(maximum):
		frappe.throw(
			frappe._("Credit load must be between {0} and {1}; selected load is {2}.").format(
				minimum, maximum, total
			)
		)
	prerequisites = frappe.get_all(
		"Curriculum Prerequisite",
		filters={"parent": doc.curriculum_version, "course": ["in", [row.course for row in doc.courses]]},
		fields=["course", "prerequisite_course"],
	)
	completed = set(
		frappe.get_all(
			"Student Academic History",
			filters={"student": doc.student, "outcome": ["in", ["Passed", "Exempted"]]},
			pluck="course",
		)
	)
	missing = [row for row in prerequisites if row.prerequisite_course not in completed]
	if missing:
		frappe.throw(
			frappe._("Prerequisite {0} is required before registering {1}.").format(
				missing[0].prerequisite_course, missing[0].course
			)
		)
	doc.total_credit_units = total


def _available_courses(registration):
	rows = frappe.get_all(
		"Curriculum Course",
		filters={
			"parent": registration.curriculum_version,
			"academic_level": registration.academic_level,
			"semester_number": frappe.db.get_value(
				"Academic Semester", registration.academic_semester, "semester_number"
			),
		},
		fields=["course", "course_title", "course_category", "credit_units"],
	)
	return {row.course: row for row in rows}


def _validate_registration_window(semester, add_drop=False):
	today = getdate(nowdate())
	end = (
		semester.add_drop_deadline or semester.registration_end_date
		if add_drop
		else semester.registration_end_date
	)
	if (
		semester.status != "Open"
		or not semester.registration_start_date
		or not end
		or not (getdate(semester.registration_start_date) <= today <= getdate(end))
	):
		frappe.throw(frappe._("Course registration is not open for this semester."))


def _curriculum(programme, session, selected=None):
	if selected:
		curriculum = frappe.get_doc("Curriculum Version", selected)
	else:
		candidate = frappe.get_all(
			"Curriculum Version",
			filters={"programme": programme, "status": "Active"},
			fields=["name", "effective_from_session", "effective_to_session"],
			order_by="creation desc",
		)
		curriculum = next(
			(
				frappe.get_doc("Curriculum Version", row.name)
				for row in candidate
				if _session_in_range(session, row.effective_from_session, row.effective_to_session)
			),
			None,
		)
	if (
		not curriculum
		or curriculum.programme != programme
		or curriculum.status != "Active"
		or not _session_in_range(session, curriculum.effective_from_session, curriculum.effective_to_session)
	):
		frappe.throw(frappe._("No Active Curriculum Version applies to this programme and session."))
	return curriculum


def _session_in_range(session, start_name, end_name=None):
	start = getdate(frappe.db.get_value("Academic Session", start_name, "start_date"))
	end = getdate(frappe.db.get_value("Academic Session", end_name, "start_date")) if end_name else None
	return getdate(session.start_date) >= start and (not end or getdate(session.start_date) <= end)


def _history(source, event_type, course=None, credit_units=None, outcome=None, details=None, **values):
	student = source.student if source.doctype != "Student Profile" else source.name
	profile = frappe.get_doc("Student Profile", student)
	history = frappe.get_doc(
		{
			"doctype": "Student Academic History",
			"student": student,
			"event_type": event_type,
			"programme": values.get("programme") or getattr(source, "programme", None) or profile.programme,
			"academic_session": values.get("academic_session") or getattr(source, "academic_session", None),
			"academic_semester": values.get("academic_semester")
			or getattr(source, "academic_semester", None),
			"academic_level": values.get("academic_level") or getattr(source, "academic_level", None),
			"course": course,
			"credit_units": credit_units,
			"outcome": outcome,
			"effective_date": values.get("effective_date") or nowdate(),
			"reference_doctype": source.doctype,
			"reference_name": source.name,
			"details": details,
			"recorded_by": frappe.session.user,
		}
	)
	history.owner = profile.user
	history.flags.academic_action = True
	history.insert(ignore_permissions=True)
	return history


def _require_student(student):
	user = frappe.db.get_value("Student Profile", student, "user")
	if frappe.session.user != user or "Student" not in frappe.get_roles():
		frappe.throw(frappe._("Only the owning Student can perform this action."), frappe.PermissionError)


def _require_role(roles, message):
	if frappe.session.user != "Administrator" and not roles.intersection(frappe.get_roles()):
		frappe.throw(frappe._(message), frappe.PermissionError)


def _lock(doctype, name):
	frappe.db.sql(f"select name from `tab{doctype}` where name=%s for update", (name,))
