import frappe
from frappe.tests import IntegrationTestCase


class TestAdmissionsConfiguration(IntegrationTestCase):
	def setUp(self):
		self.suffix = frappe.generate_hash(length=6).upper()
		self.institution = (
			frappe.db.get_value("Institution", {}, "name")
			or self._insert(
				"Institution",
				institution_code="TEST-INST",
				institution_name="Test Institution",
				institution_type="College",
			).name
		)
		self.session = self._insert(
			"Academic Session",
			session_code=f"ADM-{self.suffix}",
			session_name="Admissions 2027",
			start_date="2027-01-01",
			end_date="2027-12-31",
		)
		faculty = self._insert(
			"Faculty",
			faculty_code=f"FAC-{self.suffix}",
			faculty_name="Admissions Science",
			institution=self.institution,
		)
		department = self._insert(
			"Department",
			department_code=f"DEP-{self.suffix}",
			department_name="Admissions Computing",
			faculty=faculty.name,
		)
		self.programme = self._insert(
			"Programme",
			programme_code=f"PRG-{self.suffix}",
			programme_name="Admissions BSc",
			department=department.name,
			award_title="BSc",
			duration_years=4,
			duration_semesters=8,
			minimum_credit_load=12,
			maximum_credit_load=24,
		)

	def test_cycle_requires_an_authorised_publisher_and_locks_after_publication(self):
		cycle = self._cycle()
		with self.assertRaises(frappe.ValidationError):
			cycle.status = "Under Review"
			cycle.save()
			cycle.status = "Published"
			cycle.save()

		cycle.reload()
		self._offering(cycle.name).insert()
		cycle.status = "Under Review"
		cycle.save()

		user = self._user("admissions-publisher@example.test", "Admissions Officer")
		frappe.set_user(user.name)
		try:
			cycle.reload()
			cycle.status = "Published"
			with self.assertRaises(frappe.PermissionError):
				cycle.save()
		finally:
			frappe.set_user("Administrator")

		cycle.reload()
		cycle.status = "Published"
		cycle.save()
		cycle.notes = "Published configuration cannot drift"
		with self.assertRaises(frappe.ValidationError):
			cycle.save()

		cycle.reload()
		cycle.status = "Closed"
		cycle.save()
		cycle.status = "Archived"
		cycle.save()

	def test_offering_validates_window_fee_and_application_fields(self):
		cycle = self._cycle()
		offering = self._offering(
			cycle.name,
			applications_open_from="2026-11-01 00:00:00",
		)
		with self.assertRaises(frappe.ValidationError):
			offering.insert()

		offering.applications_open_from = None
		offering.application_fee = 0
		offering.require_payment_before_submission = 1
		with self.assertRaises(frappe.ValidationError):
			offering.insert()

		offering.application_fee = 5000
		offering.append(
			"application_fields",
			{
				"field_key": "certificate",
				"label": "Certificate",
				"field_type": "Attachment",
				"is_required": 1,
				"allowed_extensions": "exe,pdf",
				"maximum_file_size_mb": 5,
			},
		)
		with self.assertRaises(frappe.ValidationError):
			offering.insert()

		offering.application_fields[0].allowed_extensions = ".PDF, jpg"
		offering.insert()
		self.assertEqual(offering.application_fields[0].allowed_extensions, "jpg,pdf")

	def test_programme_and_campus_are_unique_within_a_cycle(self):
		cycle = self._cycle()
		self._offering(cycle.name).insert()
		with self.assertRaises(frappe.ValidationError):
			self._offering(cycle.name).insert()

	def test_admissions_permissions_and_audit_are_applied(self):
		cycle = self._cycle()
		user = self._user("admissions-officer@example.test", "Admissions Officer")
		frappe.set_user(user.name)
		try:
			self.assertTrue(frappe.has_permission("Admission Cycle", "create"))
			self.assertTrue(frappe.has_permission("Admission Programme", "write"))
			self.assertFalse(frappe.has_permission("Domain Audit Event", "read"))
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(
			frappe.db.exists(
				"Domain Audit Event",
				{"action": "Created", "resource_type": "Admission Cycle", "resource_name": cycle.name},
			)
		)

	def _cycle(self):
		return self._insert(
			"Admission Cycle",
			admission_cycle_code=f"CYC-{self.suffix}",
			cycle_name="Test 2027 Admissions",
			academic_session=self.session.name,
			applications_open_from="2026-12-01 08:00:00",
			applications_close_at="2027-03-31 23:59:59",
			decision_deadline="2027-05-01",
		)

	def _offering(self, cycle, **values):
		return frappe.get_doc(
			{
				"doctype": "Admission Programme",
				"admission_cycle": cycle,
				"programme": self.programme.name,
				"application_fee": 5000,
				"currency": "NGN",
				**values,
			}
		)

	@staticmethod
	def _user(email, role):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Admissions",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		return user

	@staticmethod
	def _insert(doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert()
