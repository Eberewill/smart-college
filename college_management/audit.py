import frappe
from frappe.utils import now_datetime

from college_management.college_management_system.doctype.base import in_schema_operation

STANDARD_FIELDS = {
	"__unsaved",
	"_comments",
	"_liked_by",
	"_seen",
	"_user_tags",
	"creation",
	"idx",
	"modified",
	"modified_by",
	"owner",
	"parent",
	"parentfield",
	"parenttype",
}
SENSITIVE_FIELDS = {"checkout_url"}


def record_update(doc, method=None):
	if in_schema_operation():
		return
	previous = doc.get_doc_before_save()
	_write_event(
		doc,
		action="Created" if previous is None else "Updated",
		previous_values=_snapshot(previous),
		resulting_values=_snapshot(doc),
	)


def record_delete(doc, method=None):
	if in_schema_operation():
		return
	_write_event(doc, action="Deleted", previous_values=_snapshot(doc))


def record_user_security_change(doc):
	if in_schema_operation():
		return
	previous = doc.get_doc_before_save()
	before, after = _user_security_snapshot(previous), _user_security_snapshot(doc)
	if before == after:
		return
	_write_event(
		doc,
		action="Account Created" if previous is None else "Account Security Changed",
		previous_values=before,
		resulting_values=after,
	)


def _write_event(doc, action, previous_values=None, resulting_values=None):
	actor = getattr(frappe.session, "user", None) or "Guest"
	frappe.get_doc(
		{
			"doctype": "Domain Audit Event",
			"event_timestamp": now_datetime(),
			"actor": actor if frappe.db.exists("User", actor) else None,
			"actor_roles": ", ".join(frappe.get_roles(actor)),
			"action": action,
			"resource_type": doc.doctype,
			"resource_name": doc.name,
			"institution": _institution(doc),
			"previous_values": frappe.as_json(previous_values) if previous_values else None,
			"resulting_values": frappe.as_json(resulting_values) if resulting_values else None,
			"reason": doc.get("change_reason"),
			"request_id": _request_header("X-Frappe-Request-Id") or frappe.generate_hash(length=16),
			"ip_address": getattr(frappe.local, "request_ip", None),
			"user_agent": _request_header("User-Agent"),
		}
	).insert(ignore_permissions=True)


def _request_header(name):
	if not getattr(frappe.local, "request", None):
		return None
	return frappe.get_request_header(name)


def _institution(doc):
	if doc.doctype == "Institution":
		return doc.name
	if doc.meta.has_field("institution") and doc.get("institution"):
		return doc.institution
	return frappe.db.get_value("Institution", {}, "name")


def _snapshot(doc):
	if not doc:
		return None
	values = doc.as_dict(no_nulls=True)
	for field in doc.meta.fields:
		if field.fieldtype == "Password" or field.fieldname in SENSITIVE_FIELDS:
			values.pop(field.fieldname, None)
	return _clean(values)


def _user_security_snapshot(doc):
	if not doc:
		return None
	return {
		"enabled": bool(doc.enabled),
		"user_type": doc.user_type,
		"roles": sorted(row.role for row in doc.roles),
	}


def _clean(value):
	if isinstance(value, dict):
		return {key: _clean(item) for key, item in value.items() if key not in STANDARD_FIELDS}
	if isinstance(value, list):
		return [_clean(item) for item in value]
	return value
