import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class CourseRegistration(Document):
	def before_naming(self):
		self.registration_number = make_autoname(
			frappe.db.get_value("Institution", {}, "course_registration_series")
		)

	def validate(self):
		if not getattr(self.flags, "academic_action", False):
			frappe.throw(frappe._("Course Registrations can only change through registration actions."))
		previous = self.get_doc_before_save()
		if previous and previous.status == "Locked":
			frappe.throw(frappe._("A Locked course registration is immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Course Registrations cannot be deleted."))
