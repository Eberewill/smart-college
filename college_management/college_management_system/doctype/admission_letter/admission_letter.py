import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or {
		"System Manager",
		"Institution Super Admin",
		"Admissions Officer",
		"Registry Officer",
		"Auditor",
	}.intersection(roles):
		return ptype == "read" or "Auditor" not in roles
	return ptype == "read" and doc.owner == user


class AdmissionLetter(Document):
	def before_naming(self):
		self.letter_number = make_autoname(frappe.db.get_value("Institution", {}, "admission_letter_series"))

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and not getattr(self.flags, "acceptance_action", False):
			frappe.throw(frappe._("Admission letters can only change through acceptance actions."))
		if previous and any(
			previous.get(field) != self.get(field)
			for field in ("admission_decision", "admission_application", "letter_number", "letter_snapshot")
		):
			frappe.throw(frappe._("Issued admission-letter content is immutable."))
		if previous and previous.acceptance_status != "Awaiting Response":
			frappe.throw(frappe._("An admission response cannot be changed."))

	def on_trash(self):
		frappe.throw(frappe._("Admission letters cannot be deleted."))
