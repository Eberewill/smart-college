import frappe
from frappe.model.document import Document

from college_management.payments import make_invoice_number


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user == "Administrator" or {
		"Finance Officer",
		"Institution Super Admin",
		"System Manager",
	}.intersection(frappe.get_roles(user)):
		return True
	return ptype == "read" and doc.owner == user


class ApplicationInvoice(Document):
	def before_naming(self):
		self.invoice_number = make_invoice_number()

	def before_validate(self):
		if self.is_new():
			self.owner = frappe.db.get_value("Admission Application", self.admission_application, "owner")

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and not getattr(self.flags, "payment_update", False):
			frappe.throw(frappe._("Application invoices can only be changed by the payment service."))
		if previous and (previous.amount != self.amount or previous.currency != self.currency):
			frappe.throw(frappe._("An issued invoice amount and currency are immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Application invoices cannot be deleted."))
