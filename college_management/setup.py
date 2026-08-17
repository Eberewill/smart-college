import frappe

ROLE_DEFINITIONS = {
	"Platform Super Admin": {"desk_access": 1, "two_factor_auth": 1},
	"Institution Super Admin": {"desk_access": 1, "two_factor_auth": 1},
	"Admissions Officer": {"desk_access": 1},
	"Registry Officer": {"desk_access": 1},
	"Finance Officer": {"desk_access": 1},
	"Examination Officer": {"desk_access": 1},
	"Academic Approver": {"desk_access": 1},
	"Lecturer": {"desk_access": 1},
	"Auditor": {"desk_access": 1},
	"Student": {"desk_access": 0},
	"Applicant": {"desk_access": 0, "home_page": "applicant"},
}
PRIVILEGED_MFA_ROLES = {"System Manager", "Platform Super Admin", "Institution Super Admin"}


def install_roles():
	"""Create missing baseline roles without overwriting site-level customisation."""
	for role_name, values in ROLE_DEFINITIONS.items():
		if frappe.db.exists("Role", role_name):
			if values.get("two_factor_auth") and not frappe.db.get_value(
				"Role", role_name, "two_factor_auth"
			):
				frappe.db.set_value("Role", role_name, "two_factor_auth", 1)
			if values.get("home_page") and not frappe.db.get_value("Role", role_name, "home_page"):
				frappe.db.set_value("Role", role_name, "home_page", values["home_page"])
			continue

		frappe.get_doc({"doctype": "Role", "role_name": role_name, **values}).insert(ignore_permissions=True)

	for role_name in PRIVILEGED_MFA_ROLES:
		if frappe.db.exists("Role", role_name) and not frappe.db.get_value(
			"Role", role_name, "two_factor_auth"
		):
			frappe.db.set_value("Role", role_name, "two_factor_auth", 1)

	if not frappe.db.get_single_value("Portal Settings", "default_role"):
		frappe.db.set_single_value("Portal Settings", "default_role", "Applicant")


def enable_privileged_mfa():
	"""Explicit production action: enable OTP-app MFA for privileged roles only."""
	frappe.only_for("System Manager")
	settings = frappe.get_single("System Settings")
	settings.enable_two_factor_auth = 1
	settings.two_factor_method = "OTP App"
	settings.bypass_2fa_for_retricted_ip_users = 0
	settings.bypass_restrict_ip_check_if_2fa_enabled = 0
	settings.save(ignore_permissions=True)
	frappe.db.set_value("Role", "All", "two_factor_auth", 0)
	install_roles()
