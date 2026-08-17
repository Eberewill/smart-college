import base64
import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, nowdate

from college_management.admissions import (
	assign_review,
	complete_review,
	convert_to_student,
	issue_admission_letter,
	record_decision,
	respond_to_admission,
)
from college_management.college_management_system.doctype.admission_application.admission_application import (
	change_application_programme,
	create_application,
	save_application_responses,
	submit_application,
)
from college_management.payments import (
	create_application_invoice,
	initialize_payment,
	paystack_webhook,
	verify_payment,
)
from college_management.www.admission import get_context as get_application_context
from college_management.www.admissions import get_context, save_applicant_profile
from college_management.www.applicant import get_context as get_applicant_home_context


class TestApplicantSubmission(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=6).upper()
		institution = frappe.db.get_value("Institution", {}, "name")
		self.institution = (
			frappe.get_doc("Institution", institution)
			if institution
			else self._insert(
				"Institution",
				institution_code="TEST-INST",
				institution_name="Test Institution",
				institution_type="College",
			)
		)
		self.session = self._insert(
			"Academic Session",
			session_code=f"SUB-{self.suffix}",
			session_name=f"Submission {self.suffix}",
			start_date=add_days(nowdate(), -30),
			end_date=add_days(nowdate(), 365),
		)
		faculty = self._insert(
			"Faculty",
			faculty_code=f"SF-{self.suffix}",
			faculty_name=f"Submission Faculty {self.suffix}",
			institution=self.institution.name,
		)
		department = self._insert(
			"Department",
			department_code=f"SD-{self.suffix}",
			department_name=f"Submission Department {self.suffix}",
			faculty=faculty.name,
		)
		self.programme = self._insert(
			"Programme",
			programme_code=f"SP-{self.suffix}",
			programme_name=f"Submission Programme {self.suffix}",
			department=department.name,
			award_title="Certificate",
			duration_years=2,
			duration_semesters=4,
			minimum_credit_load=6,
			maximum_credit_load=18,
		)

	def test_applicant_role_provisions_owned_profile_and_security_audit(self):
		user, profile = self._applicant()
		self.assertEqual(profile.owner, user.name)
		self.assertTrue(profile.applicant_number.startswith("APP-"))
		self.assertEqual(frappe.db.get_single_value("Portal Settings", "default_role"), "Applicant")
		self.assertTrue(
			frappe.db.exists(
				"Domain Audit Event",
				{"resource_type": "User", "resource_name": user.name, "action": "Account Created"},
			)
		)

	def test_applicant_can_create_only_an_owned_draft(self):
		offering = self._published_offering()
		first_user, first_profile = self._applicant()
		second_user, _ = self._applicant()

		frappe.set_user(first_user.name)
		application_name = create_application(offering.name)["application"]
		application = frappe.get_doc("Admission Application", application_name)
		self.assertEqual(application.owner, first_user.name)

		frappe.set_user(second_user.name)
		try:
			with self.assertRaises(frappe.PermissionError):
				self._insert(
					"Admission Application",
					applicant_profile=first_profile.name,
					admission_programme=offering.name,
				)
			self.assertFalse(application.has_permission("read"))
		finally:
			frappe.set_user("Administrator")

	def test_applicant_can_change_programme_before_submission(self):
		first_offering = self._published_offering(
			application_fields=[self._field("old_answer", "Old Answer", "Data")]
		)
		self.suffix = frappe.generate_hash(length=6).upper()
		second_offering = self._published_offering(
			application_fields=[self._field("new_answer", "New Answer", "Data")]
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		application = create_application(first_offering.name)["application"]
		save_application_responses(
			application, [{"field_key": "old_answer", "response_value": "Discard me"}]
		)
		result = change_application_programme(application, second_offering.name)
		doc = frappe.get_doc("Admission Application", application)
		self.assertEqual(result["admission_programme"], second_offering.name)
		self.assertEqual(doc.admission_programme, second_offering.name)
		self.assertEqual(doc.programme, second_offering.programme)
		self.assertFalse(doc.responses)
		frappe.set_user("Administrator")

	def test_portal_context_and_response_action_are_owner_scoped(self):
		offering = self._published_offering(
			application_fields=[self._field("surname", "Surname", "Data", required=1)]
		)
		first_user, _ = self._applicant()
		second_user, _ = self._applicant()
		frappe.set_user(first_user.name)
		first_application = create_application(offering.name)["application"]
		with self.assertRaises(frappe.ValidationError):
			save_application_responses(
				first_application,
				[{"field_key": "unconfigured", "response_value": "Injected"}],
			)
		save_application_responses(
			first_application,
			[{"field_key": "surname", "response_value": "Applicant"}],
		)
		submit_application(first_application)
		frappe.set_user(second_user.name)
		second_application = create_application(offering.name)["application"]
		frappe.set_user(first_user.name)
		context = frappe._dict()
		get_context(context)
		self.assertEqual([item.name for item in context.applications], [first_application])
		self.assertNotIn(second_application, [item.name for item in context.applications])
		self.assertEqual(context.applications[0].status, "Submitted")
		self.assertEqual(context.applications[0].progress, 100)
		self.assertTrue(context.applications[0].submitted_at)
		self.assertEqual(context.applications[0].url, f"/admissions/{first_application}")
		self.assertFalse(context.show_sidebar)
		self.assertEqual(context.full_name, "Test Applicant")
		home_context = frappe._dict()
		get_applicant_home_context(home_context)
		self.assertEqual(home_context.profile.user, first_user.name)
		self.assertEqual(home_context.institution.institution_name, self.institution.institution_name)
		self.assertEqual(home_context.application_count, 1)
		self.assertEqual(home_context.draft_count, 0)
		self.assertIn("date_of_birth", home_context.missing_profile_fields)
		self.assertEqual(home_context.profile_action_url, "/admissions")
		frappe.form_dict = frappe._dict(application=first_application)
		application_context = frappe._dict()
		get_application_context(application_context)
		self.assertEqual(application_context.application.fields[0].value, "Applicant")
		self.assertFalse(application_context.show_sidebar)
		self.assertEqual(application_context.full_name, "Test Applicant")
		frappe.set_user(second_user.name)
		with self.assertRaises(frappe.PermissionError):
			get_application_context(frappe._dict())
		frappe.set_user("Administrator")

	def test_configurable_application_steps_and_profile_autosave(self):
		steps = [
			{"step_key": "bio", "step_title": "Personal information", "step_type": "Applicant Details"},
			{
				"step_key": "programme",
				"step_title": "Programme selection",
				"step_type": "Programme Selection",
			},
			{"step_key": "education", "step_title": "Education", "step_type": "Application Fields"},
			{"step_key": "documents", "step_title": "Documents", "step_type": "Application Fields"},
			{"step_key": "fee", "step_title": "Payment", "step_type": "Payment"},
			{"step_key": "confirm", "step_title": "Confirm", "step_type": "Review & Submit"},
		]
		offering = self._published_offering(
			application_fee=1000,
			require_payment_before_submission=1,
			application_steps=steps,
			application_fields=[
				{
					**self._field("study_mode", "Study Mode", "Select", options="Full-time\nPart-time"),
					"application_step": "programme",
				},
				{**self._field("school", "Previous School", "Data"), "application_step": "education"},
				{
					**self._field("result", "Result", "Attachment"),
					"application_step": "documents",
					"allowed_extensions": "pdf",
					"maximum_file_size_mb": 2,
				},
			],
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		application = create_application(offering.name)["application"]
		save_applicant_profile({"first_name": "Ada", "last_name": "Lovelace"})
		context = frappe._dict()
		frappe.form_dict = frappe._dict(application=application)
		get_application_context(context)
		card = context.application
		self.assertEqual([step.key for step in card.steps], [row["step_key"] for row in steps])
		self.assertEqual([step.title for step in card.steps], [row["step_title"] for row in steps])
		self.assertEqual([step.type for step in card.steps], [row["step_type"] for row in steps])
		self.assertEqual(card.steps[1].fields[0].key, "study_mode")
		self.assertEqual(card.steps[2].fields[0].key, "school")
		self.assertEqual(card.steps[3].fields[0].key, "result")
		self.assertEqual(card.programme_selection.programme, self.programme.programme_name)
		self.assertTrue(card.require_payment)
		self.assertEqual(context.application_url, f"/admissions/{application}")
		self.assertEqual(
			{field.key for field in card.profile_fields},
			{
				"first_name",
				"middle_name",
				"last_name",
				"date_of_birth",
				"gender",
				"phone",
				"nationality",
				"state_of_origin",
				"local_government_area",
				"address",
			},
		)
		self.assertEqual(
			frappe.db.get_value("Applicant Profile", {"user": user.name}, "last_name"), "Lovelace"
		)
		with self.assertRaises(frappe.ValidationError):
			save_applicant_profile({"status": "Archived"})
		frappe.set_user("Administrator")

	def test_submission_requires_complete_valid_responses_and_becomes_immutable(self):
		offering = self._published_offering(
			application_fields=[
				self._field("surname", "Surname", "Data", required=1),
				self._field("entry_route", "Entry Route", "Select", required=1, options="Direct\nUTME"),
			]
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = frappe.get_doc(
				"Admission Application", create_application(offering.name)["application"]
			)
			application.status = "Submitted"
			with self.assertRaises(frappe.ValidationError):
				application.save()

			application.reload()
			application.append("responses", {"field_key": "surname", "response_value": "Applicant"})
			application.save()
			with self.assertRaises(frappe.ValidationError):
				submit_application(application.name)

			application.reload()
			application.append("responses", {"field_key": "entry_route", "response_value": "Direct"})
			application.save()
			result = submit_application(application.name)
			self.assertEqual(result["status"], "Submitted")

			application.reload()
			snapshot = json.loads(application.submission_snapshot)
			self.assertEqual(snapshot["applicant"]["applicant_number"], application.applicant_profile)
			self.assertEqual(len(snapshot["responses"]), 2)
			application.responses[0].response_value = "Changed"
			with self.assertRaises(frappe.PermissionError):
				application.save()
		finally:
			frappe.set_user("Administrator")

	def test_default_application_steps_remain_complete(self):
		offering = self._published_offering(
			application_fee=1000,
			require_payment_before_submission=1,
			application_fields=[
				self._field("school", "Previous School", "Data"),
				{
					**self._field("result", "Result", "Attachment"),
					"allowed_extensions": "pdf",
					"maximum_file_size_mb": 2,
				},
			],
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = create_application(offering.name)["application"]
			frappe.form_dict = frappe._dict(application=application)
			context = frappe._dict()
			get_application_context(context)
			self.assertEqual(
				[step.type for step in context.application.steps],
				[
					"Applicant Details",
					"Programme Selection",
					"Application Fields",
					"Application Fields",
					"Payment",
					"Review & Submit",
				],
			)
		finally:
			frappe.set_user("Administrator")

	def test_payment_required_submission_fails_closed(self):
		offering = self._published_offering(
			application_fee=5000,
			require_payment_before_submission=1,
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = create_application(offering.name)["application"]
			with self.assertRaises(frappe.ValidationError):
				submit_application(application)
		finally:
			frappe.set_user("Administrator")

	def test_verified_payment_pays_invoice_issues_one_receipt_and_allows_submission(self):
		offering = self._published_offering(application_fee=5000, require_payment_before_submission=1)
		self._gateway()
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = create_application(offering.name)["application"]
			invoice = create_application_invoice(application)
			with patch(
				"college_management.payments.requests.post",
				return_value=self._response(
					{
						"status": True,
						"data": {
							"reference": "placeholder",
							"authorization_url": "https://checkout.paystack.com/test",
							"access_code": "access",
						},
					}
				),
			) as post:
				# Paystack must echo our generated reference, so let the mock copy it from the request.
				post.side_effect = lambda *args, **kwargs: self._response(
					{
						"status": True,
						"data": {
							"reference": kwargs["json"]["reference"],
							"authorization_url": "https://checkout.paystack.com/test",
							"access_code": "access",
						},
					}
				)
				payment = initialize_payment(invoice["invoice"])
				retry = initialize_payment(invoice["invoice"])
				self.assertEqual(post.call_args.kwargs["json"]["amount"], 500000)
				self.assertNotIn("secret", json.dumps(post.call_args.kwargs["json"]))
				self.assertEqual(retry["reference"], payment["reference"])
				self.assertEqual(post.call_count, 1)
			verification = {
				"id": 123456789012,
				"reference": payment["reference"],
				"amount": 500000,
				"currency": "NGN",
				"status": "success",
				"gateway_response": "Successful",
				"paid_at": now_datetime(),
			}
			with patch("college_management.payments._fetch_verification", return_value=verification):
				self.assertEqual(verify_payment(payment["reference"])["invoice_status"], "Paid")
				self.assertEqual(verify_payment(payment["reference"])["invoice_status"], "Paid")
			self.assertEqual(
				frappe.db.count("Application Payment Receipt", {"application_invoice": invoice["invoice"]}), 1
			)
			self.assertEqual(submit_application(application)["status"], "Submitted")
		finally:
			frappe.set_user("Administrator")

	def test_verification_mismatch_never_credits_the_invoice(self):
		offering = self._published_offering(application_fee=5000, require_payment_before_submission=1)
		self._gateway()
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = create_application(offering.name)["application"]
			invoice = create_application_invoice(application)["invoice"]
			with patch("college_management.payments.requests.post") as post:
				post.side_effect = lambda *args, **kwargs: self._response(
					{
						"status": True,
						"data": {
							"reference": kwargs["json"]["reference"],
							"authorization_url": "https://checkout.paystack.com/test",
						},
					}
				)
				reference = initialize_payment(invoice)["reference"]
			with patch(
				"college_management.payments._fetch_verification",
				return_value={
					"id": 2,
					"reference": reference,
					"amount": 499900,
					"currency": "NGN",
					"status": "success",
				},
			):
				result = verify_payment(reference)
			self.assertEqual(result["reconciliation_status"], "Amount Mismatch")
			self.assertNotEqual(result["invoice_status"], "Paid")
			self.assertFalse(
				frappe.db.exists("Application Payment Receipt", {"application_invoice": invoice})
			)
		finally:
			frappe.set_user("Administrator")

	def test_webhook_signature_and_payload_hash_are_idempotent(self):
		gateway = self._gateway()
		audit = frappe.db.get_value(
			"Domain Audit Event",
			{"resource_type": "Payment Gateway Configuration", "resource_name": gateway.name},
			"resulting_values",
		)
		self.assertNotIn("sk_test_college", audit)
		self.assertNotIn("secret_key", audit)
		payload = json.dumps({"event": "charge.success", "data": {"reference": "unknown"}}).encode()
		signature = hmac.new(b"sk_test_college", payload, hashlib.sha512).hexdigest()
		request = Mock()
		request.get_data.return_value = payload
		with (
			patch.object(frappe, "request", request),
			patch.object(frappe, "get_request_header", return_value="invalid"),
		):
			with self.assertRaises(frappe.PermissionError):
				paystack_webhook()
		with (
			patch.object(frappe, "request", request),
			patch.object(frappe, "get_request_header", return_value=signature),
			patch.object(frappe, "enqueue"),
		):
			self.assertEqual(paystack_webhook()["status"], "received")
			self.assertEqual(paystack_webhook()["status"], "duplicate")
		self.assertEqual(
			frappe.db.count("Payment Webhook Event", {"payload_hash": hashlib.sha256(payload).hexdigest()}), 1
		)

	def test_review_decision_acceptance_and_student_conversion_are_governed(self):
		offering = self._published_offering(
			review_stages=[
				{
					"stage_code": "screening",
					"stage_name": "Document Screening",
					"reviewer_role": "Admissions Officer",
					"max_score": 100,
					"pass_score": 60,
					"checklist_items": "Identity document\nEntry qualification",
				}
			]
		)
		applicant, _ = self._applicant()
		reviewer = self._staff("Admissions Officer")
		decision_maker = self._staff("Admissions Officer")
		registry = self._staff("Registry Officer")
		frappe.set_user(applicant.name)
		application = create_application(offering.name)["application"]
		submit_application(application)

		frappe.set_user("Administrator")
		review_name = assign_review(application, "screening", reviewer.name)["review"]
		frappe.set_user(applicant.name)
		self.assertFalse(frappe.get_doc("Admission Review", review_name).has_permission("read"))
		frappe.set_user(reviewer.name)
		with self.assertRaises(frappe.ValidationError):
			complete_review(
				review_name,
				{"Identity document": "Pass"},
				80,
				"Recommend Admission",
			)
		complete_review(
			review_name,
			{
				"Identity document": "Pass",
				"Entry qualification": {"result": "Pass", "notes": "Verified"},
			},
			80,
			"Recommend Admission",
			"Requirements verified.",
		)
		with self.assertRaises(frappe.PermissionError):
			record_decision(application, "Admitted", "Meets entry requirements")

		frappe.set_user(decision_maker.name)
		decision = record_decision(application, "Admitted", "Meets entry requirements")["decision"]
		letter = issue_admission_letter(decision, add_days(nowdate(), 14))["letter"]
		self.assertEqual(issue_admission_letter(decision, add_days(nowdate(), 14))["letter"], letter)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Admission Decision", decision).save()

		frappe.set_user(applicant.name)
		applicant_decision = frappe.get_doc("Admission Decision", decision)
		self.assertTrue(applicant_decision.has_permission("read"))
		applicant_decision.apply_fieldlevel_read_permissions()
		self.assertFalse(applicant_decision.get("review_summary"))
		self.assertEqual(respond_to_admission(letter, "Accepted")["status"], "Accepted")
		with self.assertRaises(frappe.ValidationError):
			respond_to_admission(letter, "Declined")

		frappe.set_user(registry.name)
		student = convert_to_student(letter)["student"]
		self.assertEqual(convert_to_student(letter)["student"], student)
		self.assertEqual(frappe.db.count("Student Profile", {"admission_application": application}), 1)
		self.assertIn("Student", frappe.get_roles(applicant.name))
		frappe.set_user(applicant.name)
		self.assertTrue(frappe.get_doc("Student Profile", student).has_permission("read"))
		frappe.set_user("Administrator")

	def test_review_stages_must_run_in_configured_order(self):
		offering = self._published_offering(
			review_stages=[
				{
					"stage_code": "documents",
					"stage_name": "Documents",
					"reviewer_role": "Admissions Officer",
					"max_score": 50,
					"pass_score": 25,
					"checklist_items": "Documents complete",
				},
				{
					"stage_code": "eligibility",
					"stage_name": "Eligibility",
					"reviewer_role": "Admissions Officer",
					"max_score": 50,
					"pass_score": 25,
					"checklist_items": "Eligible programme choice",
				},
			]
		)
		applicant, _ = self._applicant()
		reviewer = self._staff("Admissions Officer")
		frappe.set_user(applicant.name)
		application = create_application(offering.name)["application"]
		submit_application(application)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			assign_review(application, "eligibility", reviewer.name)
		first = assign_review(application, "documents", reviewer.name)["review"]
		frappe.set_user(reviewer.name)
		with self.assertRaises(frappe.ValidationError):
			complete_review(first, {"Documents complete": "Pass"}, 20, "Recommend Admission")
		complete_review(first, {"Documents complete": "Pass"}, 30, "Recommend Admission")
		frappe.set_user("Administrator")
		self.assertEqual(assign_review(application, "eligibility", reviewer.name)["status"], "Assigned")

	def test_attachment_requires_private_owned_file_with_matching_signature(self):
		offering = self._published_offering(
			application_fields=[
				{
					**self._field("portrait", "Portrait", "Attachment"),
					"allowed_extensions": "jpg",
					"maximum_file_size_mb": 2,
				},
				{
					**self._field("certificate", "Certificate", "Attachment", required=1),
					"allowed_extensions": "png",
					"maximum_file_size_mb": 2,
				},
			]
		)
		user, _ = self._applicant()
		frappe.set_user(user.name)
		try:
			application = frappe.get_doc(
				"Admission Application", create_application(offering.name)["application"]
			)
			png = base64.b64decode(
				"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
			)
			bad_file = self._file(application.name, "bad.png", png)
			frappe.db.set_value("File", bad_file.name, "file_name", "forged.jpg")
			application.append("responses", {"field_key": "portrait", "attachment": bad_file.file_url})
			with self.assertRaises(frappe.ValidationError):
				application.save()

			application.reload()
			good_file = self._file(application.name, "good.png", png + b"\n")
			application.append("responses", {"field_key": "certificate", "attachment": good_file.file_url})
			application.save()
			self.assertEqual(submit_application(application.name)["status"], "Submitted")
			application.reload()
			self.assertFalse(application.has_permission("write"))
			stored_file = frappe.get_doc("File", good_file.name)
			self.assertEqual(stored_file.attached_to_doctype, "Admission Application")
			self.assertEqual(stored_file.attached_to_name, application.name)
			self.assertFalse(stored_file.has_permission("delete"))
			with self.assertRaises(frappe.PermissionError):
				stored_file.delete()
		finally:
			frappe.set_user("Administrator")

	def _published_offering(self, application_fields=None, **values):
		cycle = self._insert(
			"Admission Cycle",
			admission_cycle_code=f"SC-{self.suffix}",
			cycle_name=f"Submission Cycle {self.suffix}",
			academic_session=self.session.name,
			applications_open_from=add_days(now_datetime(), -1),
			applications_close_at=add_days(now_datetime(), 30),
			decision_deadline=add_days(nowdate(), 60),
		)
		offering = self._insert(
			"Admission Programme",
			admission_cycle=cycle.name,
			programme=self.programme.name,
			application_fee=values.pop("application_fee", 0),
			currency="NGN",
			application_fields=application_fields or [],
			**values,
		)
		cycle.status = "Under Review"
		cycle.save()
		cycle.status = "Published"
		cycle.save()
		return offering

	def _applicant(self):
		email = f"applicant-{frappe.generate_hash(length=8)}@example.test"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Test",
				"last_name": "Applicant",
				"enabled": 1,
				"user_type": "Website User",
				"send_welcome_email": 0,
				"roles": [{"role": "Applicant"}],
			}
		).insert(ignore_permissions=True)
		return user, frappe.get_doc("Applicant Profile", {"user": user.name})

	def _gateway(self):
		existing = frappe.db.get_value(
			"Payment Gateway Configuration", {"provider": "Paystack", "enabled": 1}, "name"
		)
		if existing:
			gateway = frappe.get_doc("Payment Gateway Configuration", existing)
			gateway.secret_key = "sk_test_college"
			gateway.public_key = "pk_test_college"
			gateway.save()
			return gateway
		return self._insert(
			"Payment Gateway Configuration",
			gateway_code=f"PAYSTACK-{self.suffix}",
			provider="Paystack",
			environment="Test",
			enabled=1,
			public_key="pk_test_college",
			secret_key="sk_test_college",
		)

	@staticmethod
	def _staff(role):
		email = f"staff-{frappe.generate_hash(length=8)}@example.test"
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Staff",
				"last_name": "Reviewer",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def _response(payload):
		response = Mock()
		response.raise_for_status.return_value = None
		response.json.return_value = payload
		return response

	@staticmethod
	def _field(key, label, field_type, required=0, options=None):
		return {
			"field_key": key,
			"label": label,
			"field_type": field_type,
			"is_required": required,
			"options": options,
		}

	@staticmethod
	def _file(application, filename, content):
		return frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"content": content,
				"is_private": 1,
				"attached_to_doctype": "Admission Application",
				"attached_to_name": application,
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def _insert(doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert()
