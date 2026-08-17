import frappe

from college_management.www.admissions import _applicant_sidebar, _application_card, _get_applicant_profile

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
	context.application_url = f"/admissions/{application.name}"
	context.profile = frappe.get_doc("Applicant Profile", profile)
	context.title = f"{context.application.programme} · {application.name}"
	context.show_sidebar = True
	context.sidebar_columns = 3
	context.sidebar_items = _applicant_sidebar()
	return context
