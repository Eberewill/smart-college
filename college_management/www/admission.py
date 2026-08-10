import frappe

from college_management.www.admissions import _applicant_sidebar, _application_card

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/admissions"
		raise frappe.Redirect
	if "Applicant" not in frappe.get_roles():
		frappe.throw(frappe._("An Applicant account is required."), frappe.PermissionError)
	profile = frappe.db.get_value("Applicant Profile", {"user": frappe.session.user}, "name")
	application_name = frappe.form_dict.get("application")
	if not profile or not application_name:
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
	context.sidebar_items = _applicant_sidebar(application)
	return context
