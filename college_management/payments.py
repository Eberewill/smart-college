import hashlib
import hmac
import json
from decimal import Decimal

import frappe
import requests
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime

PAYSTACK_API = "https://api.paystack.co"
FINANCE_ROLES = {"Finance Officer", "Institution Super Admin", "System Manager"}


def _configuration():
	name = frappe.db.get_value(
		"Payment Gateway Configuration", {"provider": "Paystack", "enabled": 1}, "name"
	)
	if not name:
		frappe.throw(frappe._("An enabled Paystack configuration is required."))
	return frappe.get_doc("Payment Gateway Configuration", name)


def _headers(configuration):
	return {
		"Authorization": f"Bearer {configuration.get_password('secret_key')}",
		"Content-Type": "application/json",
	}


def _subunits(amount):
	return int(Decimal(str(amount)) * 100)


def _assert_owner_or_finance(application_owner):
	if frappe.session.user == "Administrator" or FINANCE_ROLES.intersection(frappe.get_roles()):
		return
	if frappe.session.user != application_owner:
		frappe.throw(frappe._("You cannot access this payment."), frappe.PermissionError)


def get_or_create_invoice(application_name):
	application = frappe.get_doc("Admission Application", application_name)
	application.check_permission("read")
	_assert_owner_or_finance(application.owner)
	existing = frappe.db.get_value("Application Invoice", {"admission_application": application.name}, "name")
	if existing:
		return frappe.get_doc("Application Invoice", existing)
	offering = frappe.get_doc("Admission Programme", application.admission_programme)
	if Decimal(str(offering.application_fee or 0)) <= 0:
		frappe.throw(frappe._("This application has no fee to invoice."))
	return frappe.get_doc(
		{
			"doctype": "Application Invoice",
			"admission_application": application.name,
			"applicant_profile": application.applicant_profile,
			"amount": offering.application_fee,
			"currency": offering.currency,
			"issued_at": now_datetime(),
			"status": "Unpaid",
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def create_application_invoice(application):
	invoice = get_or_create_invoice(application)
	return {
		"invoice": invoice.name,
		"status": invoice.status,
		"amount": invoice.amount,
		"currency": invoice.currency,
	}


@frappe.whitelist(methods=["POST"])
def initialize_payment(invoice):
	frappe.db.sql("select name from `tabApplication Invoice` where name=%s for update", (invoice,))
	invoice_doc = frappe.get_doc("Application Invoice", invoice)
	_assert_owner_or_finance(invoice_doc.owner)
	if invoice_doc.status == "Paid":
		frappe.throw(frappe._("This invoice is already paid."))
	active = frappe.db.get_value(
		"Application Payment Transaction",
		{"application_invoice": invoice_doc.name, "status": ["in", ("Initialized", "Pending")]},
		["payment_reference", "checkout_url"],
		as_dict=True,
	)
	if active and active.checkout_url:
		return {"reference": active.payment_reference, "authorization_url": active.checkout_url}
	configuration = _configuration()
	reference = f"CM-{frappe.generate_hash(length=24)}"
	transaction = frappe.get_doc(
		{
			"doctype": "Application Payment Transaction",
			"payment_reference": reference,
			"application_invoice": invoice_doc.name,
			"provider": configuration.provider,
			"amount": invoice_doc.amount,
			"currency": invoice_doc.currency,
			"status": "Initialized",
			"reconciliation_status": "Not Verified",
		}
	).insert(ignore_permissions=True)
	email = frappe.db.get_value("Applicant Profile", invoice_doc.applicant_profile, "user")
	try:
		response = requests.post(
			f"{PAYSTACK_API}/transaction/initialize",
			headers=_headers(configuration),
			json={
				"email": email,
				"amount": _subunits(invoice_doc.amount),
				"currency": invoice_doc.currency,
				"reference": reference,
				"metadata": {"invoice": invoice_doc.name, "application": invoice_doc.admission_application},
			},
			timeout=(5, 20),
		)
		response.raise_for_status()
		payload = response.json()
		data = payload.get("data") or {}
		if (
			not payload.get("status")
			or data.get("reference") != reference
			or not data.get("authorization_url")
		):
			raise ValueError("Unexpected gateway response")
	except (requests.RequestException, ValueError, TypeError) as exc:
		transaction.status = "Failed"
		transaction.gateway_message = str(exc)[:500]
		transaction.flags.payment_update = True
		transaction.save(ignore_permissions=True)
		frappe.throw(frappe._("The payment gateway could not initialize this payment. Please retry."))
	transaction.checkout_url = data["authorization_url"]
	transaction.flags.payment_update = True
	transaction.save(ignore_permissions=True)
	invoice_doc.status = "Pending"
	invoice_doc.flags.payment_update = True
	invoice_doc.save(ignore_permissions=True)
	return {"reference": reference, "authorization_url": transaction.checkout_url}


def _fetch_verification(reference):
	configuration = _configuration()
	response = requests.get(
		f"{PAYSTACK_API}/transaction/verify/{reference}",
		headers=_headers(configuration),
		timeout=(5, 20),
	)
	response.raise_for_status()
	payload = response.json()
	if not payload.get("status") or not payload.get("data"):
		raise ValueError("Unexpected gateway response")
	return payload["data"]


def _apply_verification(reference, data):
	# Serialize concurrent callback, webhook, and manual reconciliation attempts.
	frappe.db.sql(
		"select name from `tabApplication Payment Transaction` where payment_reference=%s for update",
		(reference,),
	)
	transaction = frappe.get_doc("Application Payment Transaction", {"payment_reference": reference})
	invoice = frappe.get_doc("Application Invoice", transaction.application_invoice)
	if transaction.status == "Successful" and invoice.status == "Paid":
		return _result(transaction, invoice)
	observed_reference = data.get("reference")
	observed_amount = int(data.get("amount") or 0)
	observed_currency = data.get("currency")
	transaction.provider_transaction_id = str(data.get("id") or "")
	transaction.gateway_message = str(data.get("gateway_response") or "")[:500]
	transaction.verified_at = now_datetime()
	transaction.observed_amount = Decimal(observed_amount) / 100
	transaction.observed_currency = observed_currency
	transaction.reconciliation_status = "Matched"
	if observed_reference != reference:
		transaction.reconciliation_status = "Reference Mismatch"
	elif observed_amount != _subunits(invoice.amount):
		transaction.reconciliation_status = "Amount Mismatch"
	elif observed_currency != invoice.currency:
		transaction.reconciliation_status = "Currency Mismatch"
	elif data.get("status") != "success":
		transaction.reconciliation_status = "Payment Not Successful"
	if transaction.reconciliation_status == "Matched":
		transaction.status = "Successful"
	elif transaction.reconciliation_status == "Payment Not Successful":
		transaction.status = "Pending"
	else:
		transaction.status = "Failed"
	transaction.flags.payment_update = True
	transaction.save(ignore_permissions=True)
	if transaction.status == "Successful":
		invoice.status = "Paid"
		invoice.paid_at = data.get("paid_at") or now_datetime()
		invoice.flags.payment_update = True
		invoice.save(ignore_permissions=True)
		_create_receipt(invoice, transaction)
	return _result(transaction, invoice)


def _create_receipt(invoice, transaction):
	if frappe.db.exists("Application Payment Receipt", {"payment_transaction": transaction.name}):
		return
	frappe.get_doc(
		{
			"doctype": "Application Payment Receipt",
			"application_invoice": invoice.name,
			"payment_transaction": transaction.name,
			"admission_application": invoice.admission_application,
			"applicant_profile": invoice.applicant_profile,
			"amount": invoice.amount,
			"currency": invoice.currency,
			"issued_at": now_datetime(),
			"verification_code": frappe.generate_hash(length=32),
		}
	).insert(ignore_permissions=True)


def _result(transaction, invoice):
	return {
		"reference": transaction.payment_reference,
		"transaction_status": transaction.status,
		"reconciliation_status": transaction.reconciliation_status,
		"invoice_status": invoice.status,
	}


@frappe.whitelist(methods=["POST"])
def verify_payment(reference):
	transaction = frappe.get_doc("Application Payment Transaction", {"payment_reference": reference})
	_assert_owner_or_finance(transaction.owner)
	try:
		return _apply_verification(reference, _fetch_verification(reference))
	except requests.RequestException, ValueError, TypeError:
		frappe.throw(frappe._("Payment verification is temporarily unavailable. Please retry."))


@frappe.whitelist(methods=["POST"])
def reconcile_payment(reference):
	if frappe.session.user != "Administrator" and not FINANCE_ROLES.intersection(frappe.get_roles()):
		frappe.throw(frappe._("Only finance administrators can reconcile payments."), frappe.PermissionError)
	return verify_payment(reference)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def paystack_webhook():
	raw = frappe.request.get_data()
	configuration = _configuration()
	expected = hmac.new(configuration.get_password("secret_key").encode(), raw, hashlib.sha512).hexdigest()
	provided = frappe.get_request_header("x-paystack-signature") or ""
	if not hmac.compare_digest(expected, provided):
		frappe.throw(frappe._("Invalid webhook signature."), frappe.PermissionError)
	payload = json.loads(raw)
	payload_hash = hashlib.sha256(raw).hexdigest()
	if frappe.db.exists("Payment Webhook Event", {"payload_hash": payload_hash}):
		return {"status": "duplicate"}
	data = payload.get("data") or {}
	try:
		event = frappe.get_doc(
			{
				"doctype": "Payment Webhook Event",
				"payload_hash": payload_hash,
				"provider": "Paystack",
				"event_type": payload.get("event"),
				"payment_reference": data.get("reference"),
				"received_at": now_datetime(),
				"processing_status": "Received",
			}
		).insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		return {"status": "duplicate"}
	frappe.enqueue(
		"college_management.payments.process_webhook_event",
		event_name=event.name,
		enqueue_after_commit=True,
	)
	return {"status": "received"}


def process_webhook_event(event_name):
	event = frappe.get_doc("Payment Webhook Event", event_name)
	if event.processing_status == "Processed":
		return
	try:
		if event.event_type != "charge.success" or not frappe.db.exists(
			"Application Payment Transaction", {"payment_reference": event.payment_reference}
		):
			event.processing_status = "Ignored"
		else:
			_apply_verification(event.payment_reference, _fetch_verification(event.payment_reference))
			event.processing_status = "Processed"
	except Exception:
		event.processing_status = "Failed"
		event.processing_error = frappe.get_traceback()[-2000:]
		raise
	finally:
		event.flags.payment_update = True
		event.save(ignore_permissions=True)


def make_invoice_number():
	return make_autoname(frappe.db.get_value("Institution", {}, "application_invoice_series"))


def make_receipt_number():
	return make_autoname(frappe.db.get_value("Institution", {}, "payment_receipt_series"))
