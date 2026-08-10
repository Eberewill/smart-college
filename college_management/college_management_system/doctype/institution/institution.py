import re

import frappe

from college_management.college_management_system.doctype.base import CodeDocument, in_schema_operation


class Institution(CodeDocument):
	code_field = "institution_code"

	def validate(self):
		super().validate()
		for field in (
			"applicant_number_series",
			"application_number_series",
			"application_invoice_series",
			"payment_receipt_series",
			"admission_letter_series",
			"student_number_series",
		):
			series = (self.get(field) or "").strip().upper()
			if not re.fullmatch(r"[A-Z0-9._/-]*#{4,}[A-Z0-9._/#-]*", series):
				frappe.throw(
					frappe._(
						"{0} must contain only safe series characters and at least four # signs."
					).format(self.meta.get_label(field))
				)
			self.set(field, series)
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
