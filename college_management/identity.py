import frappe

from college_management.audit import record_user_security_change


def user_updated(doc, method=None):
	provision_applicant_profile(doc)
	record_user_security_change(doc)


def provision_applicant_profile(user):
	profile_name = frappe.db.get_value("Applicant Profile", {"user": user.name}, "name")
	if (
		user.enabled
		and user.user_type == "Website User"
		and "Applicant" in {row.role for row in user.roles}
		and not profile_name
	):
		profile = frappe.get_doc(
			{
				"doctype": "Applicant Profile",
				"user": user.name,
				"first_name": user.first_name,
				"middle_name": user.middle_name,
				"last_name": user.last_name,
			}
		)
		profile.insert(ignore_permissions=True)
		frappe.db.set_value("Applicant Profile", profile.name, "owner", user.name, update_modified=False)
	elif profile_name:
		status = frappe.db.get_value("Applicant Profile", profile_name, "status")
		if not user.enabled and status == "Active":
			frappe.db.set_value("Applicant Profile", profile_name, "status", "Suspended")
		elif user.enabled and status == "Suspended":
			frappe.db.set_value("Applicant Profile", profile_name, "status", "Active")
