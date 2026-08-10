import frappe
from frappe.model.document import Document


class PaymentGatewayConfiguration(Document):
	def validate(self):
		if self.provider != "Paystack":
			frappe.throw(frappe._("Paystack is the only supported payment provider."))
		if self.enabled and not self.secret_key:
			frappe.throw(frappe._("A Secret Key is required for an enabled gateway."))
		if self.enabled and frappe.db.exists(
			"Payment Gateway Configuration",
			{"provider": self.provider, "enabled": 1, "name": ["!=", self.name or ""]},
		):
			frappe.throw(frappe._("Only one configuration per payment provider can be enabled."))

	def on_trash(self):
		if frappe.db.exists("Application Payment Transaction", {"provider": self.provider}):
			frappe.throw(frappe._("Disable a used payment gateway instead of deleting it."))
