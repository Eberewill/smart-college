import frappe
from frappe.utils import cint

from college_management.college_management_system.doctype.base import CodeDocument


class AcademicLevel(CodeDocument):
	code_field = "level_code"

	def validate(self):
		super().validate()
		if cint(self.sequence) < 1:
			frappe.throw(frappe._("Sequence must be greater than zero."))
