import frappe

no_cache = 1

PROFILE_FIELDS = (
	("first_name", "First Name", "Data", True),
	("middle_name", "Middle Name", "Data", False),
	("last_name", "Last Name", "Data", False),
	("date_of_birth", "Date of Birth", "Date", False),
	("gender", "Gender", "Select", False),
	("phone", "Phone", "Data", False),
	("nationality", "Nationality", "Data", False),
	("state_of_origin", "State of Origin", "Data", False),
	("local_government_area", "Local Government Area", "Data", False),
	("address", "Address", "Small Text", False),
)


def get_context(context):
	profile = _get_applicant_profile()
	context.title = "Applications"
	_set_portal_identity(context, profile)
	application_names = frappe.get_all(
		"Admission Application",
		filters={"applicant_profile": profile},
		pluck="name",
		order_by="creation desc",
	)
	context.applications = [_application_summary(name) for name in application_names]
	return context


def _set_portal_identity(context, profile_name):
	profile = frappe.get_doc("Applicant Profile", profile_name)
	institution = frappe.db.get_value(
		"Institution",
		{"is_active": 1},
		["institution_name", "logo", "primary_color", "secondary_color"],
		as_dict=True,
	) or frappe._dict()
	full_name = " ".join(
		part for part in (profile.first_name, profile.middle_name, profile.last_name) if part
	)
	context.body_class = "cm-applicant-portal"
	context.show_sidebar = False
	context.profile = profile
	context.full_name = full_name
	context.initials = "".join(
		part[0].upper() for part in (profile.first_name, profile.last_name) if part
	) or profile.first_name[0].upper()
	context.institution = institution
	context.brand_primary = institution.primary_color or "#07366f"
	context.brand_accent = institution.secondary_color or "#008f89"


def _applicant_sidebar():
	links = [
		frappe._dict(title="Home", route="/applicant"),
		frappe._dict(title="Applications", route="/admissions"),
	]
	if "Student" in frappe.get_roles():
		links.append(frappe._dict(title="Student Academics", route="/student"))
	return [frappe._dict(group_title="Applicant portal", group_items=links)]


def _get_applicant_profile():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/applicant"
		raise frappe.Redirect
	if "Applicant" not in frappe.get_roles():
		frappe.throw(frappe._("An Applicant account is required."), frappe.PermissionError)
	profile = frappe.db.get_value("Applicant Profile", {"user": frappe.session.user}, "name")
	if not profile:
		frappe.throw(frappe._("Your Applicant Profile is not available."), frappe.PermissionError)
	return profile


def _application_summary(name):
	application = frappe.get_doc("Admission Application", name)
	card = _application_card(name)
	return frappe._dict(
		name=application.name,
		status=application.status,
		admission_programme=application.admission_programme,
		programme=card.programme,
		application_type=card.application_type,
		academic_session=card.academic_session,
		modified=application.modified,
		submitted_at=application.submitted_at,
		progress=_application_progress(card),
		url=f"/admissions/{application.name}",
	)


def _application_progress(card):
	if card.status == "Submitted":
		return 100

	completed = 0
	for step in card.steps:
		if step.type == "Applicant Details":
			complete = all(not field.required or field.value for field in card.profile_fields)
		elif step.type in {"Application Fields", "Programme Selection"}:
			complete = all(
				not field.required or field.value or field.attachment for field in step.fields
			)
		elif step.type == "Payment":
			complete = not card.require_payment or (
				card.transaction and card.transaction.status == "Successful"
			)
		else:
			complete = False
		completed += bool(complete)
	return round(completed / len(card.steps) * 100) if card.steps else 0


def _application_card(name):
	application = frappe.get_doc("Admission Application", name)
	offering = frappe.get_doc("Admission Programme", application.admission_programme)
	programme = frappe.db.get_value(
		"Programme",
		application.programme,
		["programme_name", "award_title", "department", "duration_years"],
		as_dict=True,
	)
	academic_session = frappe.db.get_value("Admission Cycle", application.admission_cycle, "academic_session")
	department = frappe.db.get_value(
		"Department", programme.department, ["department_name", "faculty"], as_dict=True
	)
	programme_selection = frappe._dict(
		application_type=programme.award_title,
		academic_session=frappe.db.get_value("Academic Session", academic_session, "session_name"),
		faculty=frappe.db.get_value("Faculty", department.faculty, "faculty_name"),
		department=department.department_name,
		programme=programme.programme_name,
		campus=frappe.db.get_value("Campus", offering.campus, "campus_name")
		if offering.campus
		else frappe._("Not specified"),
		duration=frappe._("{0} years").format(programme.duration_years),
	)
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
	fields = [
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
			step=(row.application_step or "").strip().lower(),
		)
		for row in offering.application_fields
	]
	return frappe._dict(
		name=application.name,
		status=application.status,
		submitted_at=application.submitted_at,
		admission_programme=application.admission_programme,
		programme=programme.programme_name,
		application_type=programme.award_title,
		academic_session=programme_selection.academic_session,
		programme_selection=programme_selection,
		programme_code=application.programme,
		application_fee=offering.application_fee,
		currency=offering.currency,
		fields=fields,
		steps=_application_steps(offering, fields),
		profile_fields=_profile_fields(application.applicant_profile),
		require_payment=offering.require_payment_before_submission,
		invoice=invoice,
		transaction=transaction,
		decision=decision,
		letter=letter,
		student=student,
	)


def _application_steps(offering, fields):
	if offering.application_steps:
		return [
			frappe._dict(
				key=row.step_key,
				title=row.step_title,
				type=row.step_type,
				description=row.description,
				fields=[field for field in fields if field.step == row.step_key],
			)
			for row in offering.application_steps
		]

	steps = [
		frappe._dict(key="details", title="Your details", type="Applicant Details"),
		frappe._dict(
			key="programme",
			title="Programme selection",
			type="Programme Selection",
			description="Confirm the programme and study options configured for this application.",
			fields=[],
		),
	]
	questions = [field for field in fields if field.type != "Attachment"]
	documents = [field for field in fields if field.type == "Attachment"]
	if questions:
		steps.append(
			frappe._dict(
				key="application", title="Application details", type="Application Fields", fields=questions
			)
		)
	if documents:
		steps.append(
			frappe._dict(
				key="documents", title="Supporting documents", type="Application Fields", fields=documents
			)
		)
	if offering.application_fee:
		steps.append(frappe._dict(key="payment", title="Application fee", type="Payment"))
	steps.append(frappe._dict(key="review", title="Review and submit", type="Review & Submit"))
	return steps


def _profile_fields(profile_name):
	profile = frappe.get_doc("Applicant Profile", profile_name)
	return [
		frappe._dict(
			key=key,
			label=label,
			type="Link" if key == "nationality" else field_type,
			required=required,
			value=profile.get(key) or "",
			options=["Female", "Male", "Other", "Prefer not to say"] if key == "gender" else [],
			link_options="Country" if key == "nationality" else None,
		)
		for key, label, field_type, required in PROFILE_FIELDS
	]


@frappe.whitelist(methods=["POST"])
def save_applicant_profile(values):
	profile_name = frappe.db.get_value("Applicant Profile", {"user": frappe.session.user}, "name")
	if not profile_name:
		frappe.throw(frappe._("Your Applicant Profile is not available."), frappe.PermissionError)
	profile = frappe.get_doc("Applicant Profile", profile_name)
	profile.check_permission("write")
	payload = frappe.parse_json(values) if isinstance(values, str) else values
	if not isinstance(payload, dict):
		frappe.throw(frappe._("Applicant details must be an object."))
	allowed = {field[0] for field in PROFILE_FIELDS}
	if set(payload) - allowed:
		frappe.throw(frappe._("Applicant details contain an unsupported field."))
	for key, value in payload.items():
		profile.set(key, value.strip() if isinstance(value, str) else value)
	profile.save()
	return {"profile": profile.name, "modified": profile.modified}


def _linked_doc(doctype, field, value):
	name = frappe.db.get_value(doctype, {field: value}, "name")
	return frappe.get_doc(doctype, name) if name else None
