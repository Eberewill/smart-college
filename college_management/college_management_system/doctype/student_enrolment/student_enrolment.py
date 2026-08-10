import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class StudentEnrolment(Document):
	def before_naming(self):
		self.enrolment_number = make_autoname(
			frappe.db.get_value("Institution", {}, "enrolment_number_series")
		)

	def validate(self):
		if not getattr(self.flags, "academic_action", False):
			frappe.throw(frappe._("Student Enrolments can only change through academic actions."))
		previous = self.get_doc_before_save()
		if previous and previous.as_dict() != self.as_dict():
			frappe.throw(frappe._("An activated Student Enrolment is immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Student Enrolments cannot be deleted."))
