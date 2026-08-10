import frappe
from frappe.model.document import Document


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or {
		"System Manager",
		"Institution Super Admin",
		"Admissions Officer",
		"Auditor",
	}.intersection(roles):
		return ptype == "read" or "Auditor" not in roles
	return ptype == "read" and doc.owner == user


class AdmissionDecision(Document):
	def validate(self):
		if self.get_doc_before_save():
			frappe.throw(frappe._("Admission decisions are immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Admission decisions cannot be deleted."))
