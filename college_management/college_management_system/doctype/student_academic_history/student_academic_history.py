import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class StudentAcademicHistory(Document):
	def before_naming(self):
		self.history_number = make_autoname(frappe.db.get_value("Institution", {}, "student_history_series"))

	def validate(self):
		if not getattr(self.flags, "academic_action", False):
			frappe.throw(frappe._("Academic History can only be created through governed actions."))
		if self.get_doc_before_save():
			frappe.throw(frappe._("Academic History is immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Academic History cannot be deleted."))
