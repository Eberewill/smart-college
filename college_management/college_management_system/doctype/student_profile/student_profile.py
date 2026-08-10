import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or {
		"System Manager",
		"Institution Super Admin",
		"Registry Officer",
		"Auditor",
	}.intersection(roles):
		return ptype == "read" or "Auditor" not in roles
	return ptype == "read" and doc.user == user


class StudentProfile(Document):
	def before_naming(self):
		self.student_number = make_autoname(frappe.db.get_value("Institution", {}, "student_number_series"))

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and not getattr(self.flags, "registry_action", False):
			frappe.throw(frappe._("Student Profiles can only change through Registry actions."))
		if previous and any(
			previous.get(field) != self.get(field)
			for field in (
				"student_number",
				"user",
				"applicant_profile",
				"admission_application",
				"programme",
				"admission_cycle",
			)
		):
			frappe.throw(frappe._("A Student Profile's admission identity is immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Student Profiles cannot be deleted. Archive the profile instead."))
