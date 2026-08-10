import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class StudentStatusChange(Document):
	def before_naming(self):
		self.change_number = make_autoname(
			frappe.db.get_value("Institution", {}, "student_status_change_series")
		)

	def validate(self):
		if not getattr(self.flags, "academic_action", False):
			frappe.throw(frappe._("Student Status Changes can only be created through Registry actions."))
		if self.get_doc_before_save():
			frappe.throw(frappe._("Student Status Changes are immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Student Status Changes cannot be deleted."))
