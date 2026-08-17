import frappe

from college_management.www.admissions import _get_applicant_profile, _set_portal_identity

no_cache = 1


def get_context(context):
	profile_name = _get_applicant_profile()
	profile = frappe.get_doc("Applicant Profile", profile_name)
	applications = frappe.get_all(
		"Admission Application",
		filters={"applicant_profile": profile_name},
		fields=["name", "status"],
		order_by="modified desc",
	)
	missing_profile_fields = [
		fieldname
		for fieldname in ("date_of_birth", "phone", "nationality", "state_of_origin", "address")
		if not profile.get(fieldname)
	]
	draft = next((application for application in applications if application.status == "Draft"), None)
	context.title = "Applicant Home"
	_set_portal_identity(context, profile_name)
	context.application_count = len(applications)
	context.draft_count = sum(application.status == "Draft" for application in applications)
	context.missing_profile_fields = missing_profile_fields
	context.profile_action_url = f"/admissions/{draft.name}" if draft else "/admissions"
	return context
