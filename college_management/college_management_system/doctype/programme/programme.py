import frappe
from frappe.utils import cint, flt

from college_management.college_management_system.doctype.base import CodeDocument


class Programme(CodeDocument):
	code_field = "programme_code"

	def validate(self):
		super().validate()
		if cint(self.duration_years) < 1 or cint(self.duration_semesters) < 1:
			frappe.throw(frappe._("Programme durations must be greater than zero."))
		if flt(self.minimum_credit_load) <= 0 or flt(self.maximum_credit_load) <= 0:
			frappe.throw(frappe._("Credit-load limits must be greater than zero."))
		if flt(self.minimum_credit_load) > flt(self.maximum_credit_load):
			frappe.throw(frappe._("Minimum Credit Load cannot exceed Maximum Credit Load."))
