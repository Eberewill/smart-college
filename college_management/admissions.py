import json

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

ADMISSIONS_ROLES = {"Admissions Officer", "Institution Super Admin", "System Manager"}
REGISTRY_ROLES = {"Registry Officer", "Institution Super Admin", "System Manager"}


def _require_role(allowed, message):
	if frappe.session.user != "Administrator" and not allowed.intersection(frappe.get_roles()):
		frappe.throw(frappe._(message), frappe.PermissionError)


def _application(application_name):
	application = frappe.get_doc("Admission Application", application_name)
	if application.status != "Submitted":
		frappe.throw(frappe._("Only a Submitted application can enter admissions review."))
	return application


def _stage(offering, stage_code):
	return next((row for row in offering.review_stages if row.stage_code == stage_code), None)


@frappe.whitelist(methods=["POST"])
def assign_review(application, stage_code, assigned_to):
	_require_role(ADMISSIONS_ROLES, "Only authorised Admissions staff can assign reviews.")
	application_doc = _application(application)
	offering = frappe.get_doc("Admission Programme", application_doc.admission_programme)
	stage = _stage(offering, stage_code)
	if not stage:
		frappe.throw(frappe._("The selected review stage is not configured for this programme."))
	if frappe.db.exists("Admission Review", {"admission_application": application, "stage_code": stage_code}):
		frappe.throw(frappe._("This review stage is already assigned."))
	prior_codes = [row.stage_code for row in offering.review_stages[: stage.idx - 1]]
	if prior_codes and frappe.db.count(
		"Admission Review",
		{"admission_application": application, "stage_code": ["in", prior_codes], "status": "Completed"},
	) != len(prior_codes):
		frappe.throw(frappe._("Complete earlier review stages before assigning this stage."))
	user = frappe.db.get_value("User", assigned_to, ["enabled", "user_type"], as_dict=True)
	if (
		not user
		or not user.enabled
		or user.user_type != "System User"
		or stage.reviewer_role not in frappe.get_roles(assigned_to)
	):
		frappe.throw(frappe._("The reviewer must be an enabled staff user with the configured role."))
	review = frappe.get_doc(
		{
			"doctype": "Admission Review",
			"admission_application": application,
			"stage_code": stage.stage_code,
			"stage_name": stage.stage_name,
			"assigned_to": assigned_to,
			"reviewer_role": stage.reviewer_role,
			"assigned_by": frappe.session.user,
			"assigned_at": now_datetime(),
			"max_score": stage.max_score,
			"pass_score": stage.pass_score,
			"checks": [
				{"check_label": item.strip(), "result": "Pending"}
				for item in stage.checklist_items.splitlines()
				if item.strip()
			],
		}
	).insert(ignore_permissions=True)
	return {"review": review.name, "status": review.status, "assigned_to": review.assigned_to}


@frappe.whitelist(methods=["POST"])
def complete_review(review, checks, score, recommendation, comments=None):
	review_doc = frappe.get_doc("Admission Review", review)
	if frappe.session.user != review_doc.assigned_to:
		frappe.throw(frappe._("Only the assigned reviewer can complete this review."), frappe.PermissionError)
	if review_doc.reviewer_role not in frappe.get_roles():
		frappe.throw(frappe._("The configured reviewer role is required."), frappe.PermissionError)
	if review_doc.status != "Assigned":
		frappe.throw(frappe._("Only an Assigned review can be completed."))
	provided = frappe.parse_json(checks) if isinstance(checks, str) else checks
	if not isinstance(provided, dict) or set(provided) != {row.check_label for row in review_doc.checks}:
		frappe.throw(frappe._("Provide one result for every configured review check."))
	for row in review_doc.checks:
		value = provided[row.check_label]
		value = {"result": value} if isinstance(value, str) else value
		if value.get("result") not in {"Pass", "Fail", "Not Applicable"}:
			frappe.throw(frappe._("Every review check requires a final result."))
		row.result = value["result"]
		row.notes = (value.get("notes") or "").strip()
		if row.result in {"Fail", "Not Applicable"} and not row.notes:
			frappe.throw(frappe._("Failed or not-applicable checks require reviewer notes."))
	if recommendation not in {"Recommend Admission", "Recommend Rejection", "Refer"}:
		frappe.throw(frappe._("Select a valid review recommendation."))
	if recommendation == "Recommend Admission" and flt(score) < flt(review_doc.pass_score):
		frappe.throw(frappe._("A score below the pass mark cannot recommend admission."))
	if recommendation == "Recommend Admission" and any(row.result == "Fail" for row in review_doc.checks):
		frappe.throw(frappe._("A failed required check cannot recommend admission."))
	if recommendation != "Recommend Admission" and not (comments or "").strip():
		frappe.throw(frappe._("Reviewer Comments are required for rejection or referral."))
	review_doc.score = score
	review_doc.recommendation = recommendation
	review_doc.reviewer_comments = (comments or "").strip()
	review_doc.completed_by = frappe.session.user
	review_doc.completed_at = now_datetime()
	review_doc.status = "Completed"
	review_doc.flags.review_action = True
	review_doc.save(ignore_permissions=True)
	return {"review": review_doc.name, "status": review_doc.status, "recommendation": recommendation}


@frappe.whitelist(methods=["POST"])
def record_decision(application, outcome, reason, conditions=None):
	_require_role(ADMISSIONS_ROLES, "Only authorised Admissions staff can record decisions.")
	application_doc = _application(application)
	frappe.db.sql("select name from `tabAdmission Application` where name=%s for update", (application,))
	if frappe.db.exists("Admission Decision", {"admission_application": application}):
		frappe.throw(frappe._("An admission decision already exists for this application."))
	if outcome not in {"Admitted", "Rejected"} or not (reason or "").strip():
		frappe.throw(frappe._("A valid outcome and decision reason are required."))
	offering = frappe.get_doc("Admission Programme", application_doc.admission_programme)
	stage_codes = [row.stage_code for row in offering.review_stages]
	if not stage_codes or frappe.db.count(
		"Admission Review",
		{"admission_application": application, "stage_code": ["in", stage_codes], "status": "Completed"},
	) != len(stage_codes):
		frappe.throw(frappe._("Every configured review stage must be completed before a decision."))
	reviews = frappe.get_all(
		"Admission Review",
		filters={"admission_application": application, "status": "Completed"},
		fields=[
			"stage_code",
			"stage_name",
			"score",
			"max_score",
			"recommendation",
			"completed_by",
			"completed_at",
		],
		order_by="creation asc",
	)
	if frappe.session.user != "Administrator" and any(
		row.completed_by == frappe.session.user for row in reviews
	):
		frappe.throw(
			frappe._("A reviewer cannot make the final decision on the same application."),
			frappe.PermissionError,
		)
	if outcome == "Admitted" and offering.capacity:
		frappe.db.sql("select name from `tabAdmission Programme` where name=%s for update", (offering.name,))
		admitted = frappe.db.sql(
			"""select count(*) from `tabAdmission Decision` decision
			join `tabAdmission Application` application
			  on application.name = decision.admission_application
			where decision.outcome='Admitted' and application.admission_programme=%s""",
			(offering.name,),
		)[0][0]
		if admitted >= offering.capacity:
			frappe.throw(frappe._("This programme has reached its admission capacity."))
	decision = frappe.get_doc(
		{
			"doctype": "Admission Decision",
			"admission_application": application,
			"outcome": outcome,
			"decision_reason": reason.strip(),
			"conditions": (conditions or "").strip(),
			"decided_by": frappe.session.user,
			"decided_at": now_datetime(),
			"review_summary": frappe.as_json(reviews, indent=2),
		}
	)
	decision.owner = application_doc.owner
	decision.insert(ignore_permissions=True)
	frappe.db.set_value(
		"Admission Decision", decision.name, "owner", application_doc.owner, update_modified=False
	)
	decision.owner = application_doc.owner
	return {"decision": decision.name, "outcome": decision.outcome}


@frappe.whitelist(methods=["POST"])
def issue_admission_letter(decision, acceptance_deadline):
	_require_role(ADMISSIONS_ROLES, "Only authorised Admissions staff can issue admission letters.")
	frappe.db.sql("select name from `tabAdmission Decision` where name=%s for update", (decision,))
	decision_doc = frappe.get_doc("Admission Decision", decision)
	if decision_doc.outcome != "Admitted":
		frappe.throw(frappe._("Only an admitted application can receive an admission letter."))
	if getdate(acceptance_deadline) < getdate(nowdate()):
		frappe.throw(frappe._("Acceptance Deadline cannot be in the past."))
	existing = frappe.db.get_value("Admission Letter", {"admission_decision": decision}, "name")
	if existing:
		return {
			"letter": existing,
			"status": frappe.db.get_value("Admission Letter", existing, "acceptance_status"),
		}
	application = frappe.get_doc("Admission Application", decision_doc.admission_application)
	offering = frappe.get_doc("Admission Programme", application.admission_programme)
	cycle = frappe.get_doc("Admission Cycle", application.admission_cycle)
	profile = frappe.get_doc("Applicant Profile", application.applicant_profile)
	institution = frappe.get_doc("Institution", frappe.db.get_value("Institution", {}, "name"))
	snapshot = {
		"institution": {
			"name": institution.institution_name,
			"address": institution.address,
			"email": institution.email,
			"phone": institution.phone,
		},
		"applicant": {
			"number": profile.applicant_number,
			"name": " ".join(filter(None, (profile.first_name, profile.middle_name, profile.last_name))),
		},
		"offer": {
			"programme": application.programme,
			"campus": offering.campus,
			"academic_session": cycle.academic_session,
			"conditions": decision_doc.conditions,
		},
	}
	letter = frappe.get_doc(
		{
			"doctype": "Admission Letter",
			"admission_decision": decision_doc.name,
			"admission_application": application.name,
			"applicant_profile": profile.name,
			"programme": application.programme,
			"admission_cycle": application.admission_cycle,
			"academic_session": cycle.academic_session,
			"campus": offering.campus,
			"issued_at": now_datetime(),
			"issued_by": frappe.session.user,
			"acceptance_deadline": acceptance_deadline,
			"conditions": decision_doc.conditions,
			"verification_code": frappe.generate_hash(length=32),
			"print_format": offering.admission_letter_print_format,
			"letter_snapshot": json.dumps(snapshot, indent=2, default=str),
		}
	)
	letter.owner = application.owner
	letter.insert(ignore_permissions=True)
	frappe.db.set_value("Admission Letter", letter.name, "owner", application.owner, update_modified=False)
	letter.owner = application.owner
	return {"letter": letter.name, "status": letter.acceptance_status}


@frappe.whitelist(methods=["POST"])
def respond_to_admission(letter, response):
	frappe.db.sql("select name from `tabAdmission Letter` where name=%s for update", (letter,))
	letter_doc = frappe.get_doc("Admission Letter", letter)
	if frappe.session.user != letter_doc.owner:
		frappe.throw(
			frappe._("Only the applicant can respond to this admission offer."), frappe.PermissionError
		)
	if letter_doc.acceptance_status != "Awaiting Response":
		frappe.throw(frappe._("This admission offer already has a final response."))
	if getdate(nowdate()) > getdate(letter_doc.acceptance_deadline):
		letter_doc.acceptance_status = "Expired"
	else:
		if response not in {"Accepted", "Declined"}:
			frappe.throw(frappe._("Response must be Accepted or Declined."))
		letter_doc.acceptance_status = response
	letter_doc.responded_at = now_datetime()
	letter_doc.flags.acceptance_action = True
	letter_doc.save(ignore_permissions=True)
	return {"letter": letter_doc.name, "status": letter_doc.acceptance_status}


@frappe.whitelist(methods=["POST"])
def convert_to_student(letter):
	_require_role(REGISTRY_ROLES, "Only authorised Registry staff can create Student Profiles.")
	frappe.db.sql("select name from `tabAdmission Letter` where name=%s for update", (letter,))
	letter_doc = frappe.get_doc("Admission Letter", letter)
	if letter_doc.acceptance_status != "Accepted":
		frappe.throw(frappe._("Only an accepted admission offer can be converted to a Student Profile."))
	existing = frappe.db.get_value(
		"Student Profile", {"admission_application": letter_doc.admission_application}, "name"
	)
	if existing:
		return {"student": existing, "status": frappe.db.get_value("Student Profile", existing, "status")}
	profile = frappe.get_doc("Applicant Profile", letter_doc.applicant_profile)
	programme = frappe.get_doc("Programme", letter_doc.programme)
	student = frappe.get_doc(
		{
			"doctype": "Student Profile",
			"user": profile.user,
			"applicant_profile": profile.name,
			"admission_application": letter_doc.admission_application,
			"programme": letter_doc.programme,
			"department": programme.department,
			"campus": letter_doc.campus,
			"admission_cycle": letter_doc.admission_cycle,
			"academic_session": letter_doc.academic_session,
			"current_level": frappe.db.get_value(
				"Academic Level", {"is_active": 1}, "name", order_by="sequence asc"
			),
			"admission_date": nowdate(),
			"first_name": profile.first_name,
			"middle_name": profile.middle_name,
			"last_name": profile.last_name,
			"date_of_birth": profile.date_of_birth,
			"gender": profile.gender,
			"phone": profile.phone,
			"contact_email": profile.user,
		}
	)
	student.owner = profile.user
	student.insert(ignore_permissions=True)
	frappe.db.set_value("Student Profile", student.name, "owner", profile.user, update_modified=False)
	student.owner = profile.user
	user = frappe.get_doc("User", profile.user)
	if "Student" not in {row.role for row in user.roles}:
		user.append("roles", {"role": "Student"})
		user.save(ignore_permissions=True)
	return {"student": student.name, "status": student.status}
