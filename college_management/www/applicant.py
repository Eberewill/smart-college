import frappe

from college_management.www.admissions import _applicant_sidebar, _get_applicant_profile

no_cache = 1


def get_context(context):
	profile_name = _get_applicant_profile()
	profile = frappe.get_doc("Applicant Profile", profile_name)
	statuses = frappe.get_all(
		"Admission Application",
		filters={"applicant_profile": profile_name},
		pluck="status",
	)
	context.title = "Applicant Home"
	context.show_sidebar = True
	context.sidebar_items = _applicant_sidebar()
	context.profile = profile
	context.full_name = " ".join(
		part for part in (profile.first_name, profile.middle_name, profile.last_name) if part
	)
	context.application_count = len(statuses)
	context.draft_count = statuses.count("Draft")
	return context
