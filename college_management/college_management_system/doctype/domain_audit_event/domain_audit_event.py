import frappe
from frappe.model.document import Document

from college_management.college_management_system.doctype.base import in_schema_operation


class DomainAuditEvent(Document):
	def validate(self):
		if not self.is_new() and not in_schema_operation():
			frappe.throw(frappe._("Domain Audit Events are append-only and cannot be changed."))

	def on_trash(self):
		if not in_schema_operation():
			frappe.throw(frappe._("Domain Audit Events cannot be deleted."))
