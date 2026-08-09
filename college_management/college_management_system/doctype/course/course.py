import frappe
from frappe.utils import flt

from college_management.college_management_system.doctype.base import CodeDocument


class Course(CodeDocument):
	code_field = "course_code"

	def validate(self):
		super().validate()
		if flt(self.default_credit_units) <= 0:
			frappe.throw(frappe._("Default Credit Units must be greater than zero."))
