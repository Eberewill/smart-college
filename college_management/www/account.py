import frappe
from frappe.core.doctype.user.user import _get_timezones

from college_management.www.applications import _get_applicant_profile, _set_portal_identity

no_cache = 1

SECTIONS = {"overview", "profile", "security", "apps"}
PROFILE_FIELDS = {"first_name", "middle_name", "last_name", "phone", "mobile_no", "language", "time_zone"}


def get_context(context):
	profile_name = _get_applicant_profile()
	section = frappe.form_dict.get("section") or "overview"
	if section not in SECTIONS:
		frappe.throw(frappe._("Account page not found."), frappe.DoesNotExistError)
	_set_portal_identity(context, profile_name)
	context.title = "My Account"
	context.section = section
	context.account_user = frappe.get_doc("User", frappe.session.user)
	context.connected_apps = _connected_apps() if section in {"overview", "apps"} else []
	if section == "profile":
		context.languages = frappe.get_all(
			"Language", filters={"enabled": 1}, fields=["name", "language_name"], order_by="language_name"
		)
		context.time_zones = _get_timezones()
	return context


def _connected_apps():
	apps = []
	for token in frappe.get_all(
		"OAuth Bearer Token",
		filters={"user": frappe.session.user},
		fields=["client"],
		distinct=True,
		order_by="creation",
	):
		connected_at = frappe.get_all(
			"OAuth Bearer Token",
			filters={"user": frappe.session.user, "client": token.client},
			pluck="creation",
			order_by="creation",
			limit=1,
		)[0]
		apps.append(
			frappe._dict(
				client=token.client,
				name=frappe.db.get_value("OAuth Client", token.client, "app_name") or token.client,
				connected_at=connected_at,
			)
		)
	return apps


@frappe.whitelist(methods=["POST"])
def save_profile(values):
	_get_applicant_profile()
	payload = frappe.parse_json(values) if isinstance(values, str) else values
	if not isinstance(payload, dict) or set(payload) - PROFILE_FIELDS:
		frappe.throw(frappe._("Profile details contain an unsupported field."))
	payload = {
		key: value.strip() if isinstance(value, str) else value for key, value in payload.items()
	}
	if not payload.get("first_name"):
		frappe.throw(frappe._("First Name is required."))

	user = frappe.get_doc("User", frappe.session.user)
	for key, value in payload.items():
		user.set(key, value)
	user.save(ignore_permissions=True)

	profile = frappe.get_doc("Applicant Profile", {"user": frappe.session.user})
	for key in ("first_name", "middle_name", "last_name"):
		profile.set(key, payload.get(key) or "")
	profile.phone = payload.get("phone") or payload.get("mobile_no") or profile.phone
	profile.save(ignore_permissions=True)
	return {"full_name": user.full_name, "profile": profile.name}


@frappe.whitelist(methods=["POST"])
def revoke_app(client):
	_get_applicant_profile()
	for token in frappe.get_all(
		"OAuth Bearer Token", filters={"user": frappe.session.user, "client": client}, pluck="name"
	):
		frappe.delete_doc("OAuth Bearer Token", token, ignore_permissions=True)
	return {"client": client, "revoked": True}
