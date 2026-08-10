import frappe
from frappe.model.document import Document

from college_management.payments import make_receipt_number


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user == "Administrator" or {
		"Finance Officer",
		"Institution Super Admin",
		"System Manager",
		"Auditor",
	}.intersection(frappe.get_roles(user)):
		return ptype == "read" or "Auditor" not in frappe.get_roles(user)
	return ptype == "read" and doc.owner == user


class ApplicationPaymentReceipt(Document):
	def before_naming(self):
		self.receipt_number = make_receipt_number()

	def before_validate(self):
		if self.is_new():
			self.owner = frappe.db.get_value("Application Invoice", self.application_invoice, "owner")

	def validate(self):
		if self.get_doc_before_save():
			frappe.throw(frappe._("Payment receipts are immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Payment receipts cannot be deleted."))
