import re

import frappe

from college_management.college_management_system.doctype.base import CodeDocument, in_schema_operation


class Institution(CodeDocument):
	code_field = "institution_code"

	def validate(self):
		super().validate()
		if self.primary_domain:
			self.primary_domain = self.primary_domain.strip().lower().rstrip(".")
			labels = self.primary_domain.split(".")
			if len(labels) < 2 or any(
				not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
			):
				frappe.throw(frappe._("Primary Domain must be a valid hostname without a protocol or path."))

	def before_insert(self):
		if frappe.db.count("Institution"):
			frappe.throw(frappe._("This site already has an Institution."))

	def on_trash(self):
		if not in_schema_operation():
			frappe.throw(frappe._("The site Institution cannot be deleted. Disable it instead."))
