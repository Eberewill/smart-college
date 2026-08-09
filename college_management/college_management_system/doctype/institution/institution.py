import frappe

from college_management.college_management_system.doctype.base import CodeDocument


class Institution(CodeDocument):
	code_field = "institution_code"

	def before_insert(self):
		if frappe.db.count("Institution"):
			frappe.throw(frappe._("This site already has an Institution."))
