from urllib.parse import quote

import frappe

from college_management.www.applications import (
	_get_applicant_profile,
	_linked_doc,
	_set_portal_identity,
)

no_cache = 1


def get_context(context):
	profile = _get_applicant_profile()
	_set_portal_identity(context, profile)
	application_names = frappe.get_all(
		"Admission Application",
		filters={"applicant_profile": profile},
		pluck="name",
	)
	decision_names = (
		frappe.get_all(
			"Admission Decision",
			filters={"admission_application": ["in", application_names]},
			pluck="name",
			order_by="decided_at desc",
		)
		if application_names
		else []
	)
	context.title = "Admissions"
	context.decisions = [_decision_card(name) for name in decision_names]
	context.offer_count = sum(decision.outcome == "Admitted" for decision in context.decisions)
	context.unsuccessful_count = sum(decision.outcome == "Rejected" for decision in context.decisions)
	context.admissions_email = frappe.db.get_value("Institution", {"is_active": 1}, "email")
	return context


def _decision_card(name):
	decision = frappe.get_doc("Admission Decision", name)
	application = frappe.get_doc("Admission Application", decision.admission_application)
	programme = frappe.db.get_value(
		"Programme",
		application.programme,
		["programme_name", "award_title"],
		as_dict=True,
	)
	academic_session = frappe.db.get_value(
		"Admission Cycle", application.admission_cycle, "academic_session"
	)
	letter = _linked_doc("Admission Letter", "admission_application", application.name)
	return frappe._dict(
		name=decision.name,
		outcome=decision.outcome,
		reason=decision.decision_reason,
		decided_at=decision.decided_at,
		application=application.name,
		programme=programme.programme_name,
		application_type=programme.award_title,
		academic_session=frappe.db.get_value("Academic Session", academic_session, "session_name"),
		application_url=f"/applications/{application.name}",
		letter=letter,
		letter_url=(
			f"/printview?doctype=Admission%20Letter&name={quote(letter.name)}" if letter else None
		),
	)
