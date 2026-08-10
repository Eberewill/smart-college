import frappe
from frappe.utils import getdate, nowdate

from college_management.academics import _available_courses

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/student"
		raise frappe.Redirect
	if "Student" not in frappe.get_roles():
		frappe.throw(frappe._("A Student account is required."), frappe.PermissionError)
	name = frappe.db.get_value("Student Profile", {"user": frappe.session.user}, "name")
	if not name:
		frappe.throw(frappe._("Your Student Profile is not available."), frappe.PermissionError)
	context.title = "Student Academics"
	context.show_sidebar = True
	context.profile = frappe.get_doc("Student Profile", name)
	context.enrolments = [
		frappe.get_doc("Student Enrolment", item)
		for item in frappe.get_all(
			"Student Enrolment", filters={"student": name}, pluck="name", order_by="creation desc"
		)
	]
	registrations = [
		frappe.get_doc("Course Registration", item)
		for item in frappe.get_all(
			"Course Registration", filters={"student": name}, pluck="name", order_by="creation desc"
		)
	]
	for registration in registrations:
		registration.available_courses = list(_available_courses(registration).values())
		registration.selected_courses = {row.course for row in registration.courses}
		semester = frappe.get_doc("Academic Semester", registration.academic_semester)
		registration.can_reopen = registration.status == "Approved" and _add_drop_open(semester)
	context.registrations = registrations
	registered_semesters = {item.academic_semester for item in registrations}
	context.open_semesters = []
	for enrolment in context.enrolments:
		if enrolment.status != "Active":
			continue
		for semester in frappe.get_all(
			"Academic Semester",
			filters={"academic_session": enrolment.academic_session, "status": "Open"},
			fields=["name", "semester_name", "registration_start_date", "registration_end_date"],
			order_by="semester_number asc",
		):
			if semester.name not in registered_semesters and _registration_open(semester):
				semester.enrolment = enrolment.name
				context.open_semesters.append(semester)
	context.history = frappe.get_all(
		"Student Academic History",
		filters={"student": name},
		fields=["event_type", "effective_date", "course", "outcome", "details"],
		order_by="effective_date desc, creation desc",
		limit=100,
	)
	return context


def _registration_open(semester):
	today = getdate(nowdate())
	return bool(
		semester.registration_start_date
		and semester.registration_end_date
		and getdate(semester.registration_start_date) <= today <= getdate(semester.registration_end_date)
	)


def _add_drop_open(semester):
	today = getdate(nowdate())
	return bool(
		semester.registration_start_date
		and semester.add_drop_deadline
		and getdate(semester.registration_start_date) <= today <= getdate(semester.add_drop_deadline)
	)
