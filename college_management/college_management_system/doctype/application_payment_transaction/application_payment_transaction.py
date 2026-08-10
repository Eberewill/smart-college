import frappe
from frappe.model.document import Document


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


class ApplicationPaymentTransaction(Document):
	def before_validate(self):
		if self.is_new():
			self.owner = frappe.db.get_value("Application Invoice", self.application_invoice, "owner")

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and not getattr(self.flags, "payment_update", False):
			frappe.throw(frappe._("Payment transactions can only be changed by the payment service."))
		if previous and any(
			previous.get(field) != self.get(field)
			for field in ("payment_reference", "application_invoice", "provider", "amount", "currency")
		):
			frappe.throw(frappe._("Payment transaction identity and expected value are immutable."))

	def on_trash(self):
		frappe.throw(frappe._("Payment transactions cannot be deleted."))
