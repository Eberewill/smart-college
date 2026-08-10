import base64
import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, nowdate

from college_management.college_management_system.doctype.admission_application.admission_application import (
	create_application,
	submit_application,
)


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
