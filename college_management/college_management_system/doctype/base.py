import re

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

CODE_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9._/-]*")


class CodeDocument(Document):
	code_field = ""

	def before_naming(self):
		self._normalise_code()

	def validate(self):
		self._normalise_code()
		code = self.get(self.code_field)
		if not CODE_PATTERN.fullmatch(code or ""):
			frappe.throw(
				frappe._(
					"{0} may contain only letters, numbers, dots, underscores, slashes, and hyphens."
				).format(self.meta.get_label(self.code_field))
			)

		previous = self.get_doc_before_save()
		if previous and previous.get(self.code_field) != code:
			frappe.throw(
				frappe._("{0} cannot be changed after creation.").format(self.meta.get_label(self.code_field))
			)

	def _normalise_code(self):
		if self.get(self.code_field):
			self.set(self.code_field, self.get(self.code_field).strip().upper())


def validate_date_range(document, start_field, end_field):
	start, end = document.get(start_field), document.get(end_field)
	if start and end and getdate(end) < getdate(start):
		frappe.throw(
			frappe._("{0} cannot be before {1}.").format(
				document.meta.get_label(end_field), document.meta.get_label(start_field)
			)
		)
