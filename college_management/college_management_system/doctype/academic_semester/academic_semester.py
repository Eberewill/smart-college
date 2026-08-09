import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate

from college_management.college_management_system.doctype.base import validate_date_range


class AcademicSemester(Document):
	def validate(self):
		if cint(self.semester_number) < 1:
			frappe.throw(frappe._("Semester Number must be greater than zero."))

		validate_date_range(self, "start_date", "end_date")
		validate_date_range(self, "registration_start_date", "registration_end_date")

		session_start, session_end = frappe.db.get_value(
			"Academic Session", self.academic_session, ["start_date", "end_date"]
		)
		for fieldname in (
			"start_date",
			"end_date",
			"registration_start_date",
			"registration_end_date",
			"add_drop_deadline",
		):
			value = self.get(fieldname)
			if value and not (getdate(session_start) <= getdate(value) <= getdate(session_end)):
				frappe.throw(
					frappe._("{0} must fall within the Academic Session.").format(
						self.meta.get_label(fieldname)
					)
				)

		if (
			self.add_drop_deadline
			and self.start_date
			and getdate(self.add_drop_deadline) < getdate(self.start_date)
		):
			frappe.throw(frappe._("Add/Drop Deadline cannot be before the semester starts."))
