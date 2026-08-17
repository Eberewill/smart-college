import frappe

from college_management.www.applications import (
	_application_card,
	_get_applicant_profile,
	_set_portal_identity,
)

no_cache = 1


def get_context(context):
	profile = _get_applicant_profile()
	application_name = frappe.form_dict.get("application")
	if not application_name:
		frappe.throw(frappe._("Application not found."), frappe.DoesNotExistError)
	application = frappe.get_doc("Admission Application", application_name)
	if application.applicant_profile != profile:
		frappe.throw(frappe._("You cannot access this application."), frappe.PermissionError)
	context.application = _application_card(application.name)
	context.application_url = f"/applications/{application.name}"
	_set_portal_identity(context, profile)
	context.title = f"{context.application.programme} · {application.name}"
	return context
