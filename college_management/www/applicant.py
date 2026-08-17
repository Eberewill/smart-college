import frappe

from college_management.www.admissions import _get_applicant_profile

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
	institution = frappe.db.get_value(
		"Institution",
		{"is_active": 1},
		["institution_name", "logo", "primary_color", "secondary_color"],
		as_dict=True,
	) or frappe._dict()
	missing_profile_fields = [
		fieldname
		for fieldname in ("date_of_birth", "phone", "nationality", "state_of_origin", "address")
		if not profile.get(fieldname)
	]
	draft = next((application for application in applications if application.status == "Draft"), None)
	context.title = "Applicant Home"
	context.body_class = "cm-applicant-portal"
	context.show_sidebar = False
	context.profile = profile
	context.full_name = " ".join(
		part for part in (profile.first_name, profile.middle_name, profile.last_name) if part
	)
	context.initials = "".join(
		part[0].upper() for part in (profile.first_name, profile.last_name) if part
	) or profile.first_name[0].upper()
	context.institution = institution
	context.brand_primary = institution.primary_color or "#07366f"
	context.brand_accent = institution.secondary_color or "#008f89"
	context.application_count = len(applications)
	context.draft_count = sum(application.status == "Draft" for application in applications)
	context.missing_profile_fields = missing_profile_fields
	context.profile_action_url = f"/admissions/{draft.name}" if draft else "/admissions"
	return context
