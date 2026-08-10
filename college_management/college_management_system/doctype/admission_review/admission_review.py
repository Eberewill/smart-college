import frappe
from frappe.model.document import Document
from frappe.utils import flt


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or {"System Manager", "Institution Super Admin", "Auditor"}.intersection(
		roles
	):
		return ptype == "read" or "Auditor" not in roles
	if "Admissions Officer" in roles:
		return ptype == "read"
	return ptype == "read" and doc.assigned_to == user


class AdmissionReview(Document):
	def before_validate(self):
		if self.is_new():
			self.assignment_key = f"{self.admission_application}::{self.stage_code}"

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and not getattr(self.flags, "review_action", False):
			frappe.throw(frappe._("Admission reviews can only be changed through review actions."))
		if previous and previous.status == "Completed":
			frappe.throw(frappe._("A completed Admission Review is immutable."))
		if previous and any(
			previous.get(field) != self.get(field)
			for field in (
				"assignment_key",
				"admission_application",
				"stage_code",
				"assigned_to",
				"max_score",
				"pass_score",
			)
		):
			frappe.throw(frappe._("An assigned review's identity and scoring rules are immutable."))
		if flt(self.score) < 0 or flt(self.score) > flt(self.max_score):
			frappe.throw(frappe._("Review Score must be between zero and Maximum Score."))

	def on_trash(self):
		frappe.throw(frappe._("Admission reviews cannot be deleted."))
