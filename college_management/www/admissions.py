import frappe
from frappe.utils import get_datetime, now_datetime

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/admissions"
		raise frappe.Redirect
	if "Applicant" not in frappe.get_roles():
		frappe.throw(frappe._("An Applicant account is required."), frappe.PermissionError)
	profile = frappe.db.get_value("Applicant Profile", {"user": frappe.session.user}, "name")
	if not profile:
		frappe.throw(frappe._("Your Applicant Profile is not available."), frappe.PermissionError)
	context.title = "Admissions"
	context.show_sidebar = True
	context.profile = frappe.get_doc("Applicant Profile", profile)
	application_names = frappe.get_all(
		"Admission Application",
		filters={"applicant_profile": profile},
		pluck="name",
		order_by="creation desc",
	)
	context.applications = [_application_card(name) for name in application_names]
	context.offerings = _open_offerings({item.admission_programme for item in context.applications})
	return context


def _open_offerings(existing_offerings):
	now = now_datetime()
	items = []
	for name in frappe.get_all(
		"Admission Programme",
		filters={"is_enabled": 1},
		pluck="name",
		order_by="creation desc",
	):
		offering = frappe.get_doc("Admission Programme", name)
		cycle = frappe.db.get_value(
			"Admission Cycle",
			offering.admission_cycle,
			["status", "applications_open_from", "applications_close_at"],
			as_dict=True,
		)
		opening = get_datetime(offering.applications_open_from or cycle.applications_open_from)
		closing = get_datetime(offering.applications_close_at or cycle.applications_close_at)
		if cycle.status == "Published" and opening <= now <= closing:
			items.append(
				frappe._dict(
					name=offering.name,
					programme=offering.programme,
					programme_name=frappe.db.get_value("Programme", offering.programme, "programme_name"),
					campus=frappe.db.get_value("Campus", offering.campus, "campus_name")
					if offering.campus
					else None,
					fee=offering.application_fee,
					currency=offering.currency,
					closing=closing,
					can_apply=offering.name not in existing_offerings,
				)
			)
	return items


def _application_card(name):
	application = frappe.get_doc("Admission Application", name)
	offering = frappe.get_doc("Admission Programme", application.admission_programme)
	responses = {row.field_key: row for row in application.responses}
	invoice = _linked_doc("Application Invoice", "admission_application", application.name)
	transaction = None
	if invoice:
		transaction_name = frappe.db.get_value(
			"Application Payment Transaction",
			{"application_invoice": invoice.name},
			"name",
			order_by="creation desc",
		)
		transaction = (
			frappe.get_doc("Application Payment Transaction", transaction_name) if transaction_name else None
		)
	decision = _linked_doc("Admission Decision", "admission_application", application.name)
	letter = _linked_doc("Admission Letter", "admission_application", application.name)
	student = _linked_doc("Student Profile", "admission_application", application.name)
	return frappe._dict(
		name=application.name,
		status=application.status,
		submitted_at=application.submitted_at,
		admission_programme=application.admission_programme,
		programme=frappe.db.get_value("Programme", application.programme, "programme_name"),
		programme_code=application.programme,
		application_fee=offering.application_fee,
		fields=[
			frappe._dict(
				key=row.field_key,
				label=row.label,
				type=row.field_type,
				required=row.is_required,
				help_text=row.help_text,
				options=[item.strip() for item in (row.options or "").splitlines() if item.strip()],
				allowed_extensions=row.allowed_extensions,
				value=responses.get(row.field_key).response_value if responses.get(row.field_key) else "",
				attachment=responses.get(row.field_key).attachment if responses.get(row.field_key) else "",
			)
			for row in offering.application_fields
		],
		invoice=invoice,
		transaction=transaction,
		decision=decision,
		letter=letter,
		student=student,
	)


def _linked_doc(doctype, field, value):
	name = frappe.db.get_value(doctype, {field: value}, "name")
	return frappe.get_doc(doctype, name) if name else None
