import frappe
from frappe.model.document import Document


class PaymentWebhookEvent(Document):
	def validate(self):
		if self.get_doc_before_save() and not getattr(self.flags, "payment_update", False):
			frappe.throw(frappe._("Webhook events can only be changed by the payment service."))

	def on_trash(self):
		frappe.throw(frappe._("Webhook events cannot be deleted."))
