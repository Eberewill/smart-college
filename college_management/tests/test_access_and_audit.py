import frappe
from frappe.tests import IntegrationTestCase

from college_management.setup import ROLE_DEFINITIONS, enable_privileged_mfa


class TestAccessAndAudit(IntegrationTestCase):
	def setUp(self):
		self.institution = (
			frappe.db.get_value("Institution", {}, "name")
			or frappe.get_doc(
				{
					"doctype": "Institution",
					"institution_code": "security-test",
					"institution_name": "Security Test Institution",
					"institution_type": "College",
				}
			)
			.insert()
			.name
		)

	def test_baseline_roles_and_mfa_marking_are_installed(self):
		self.assertEqual(
			set(ROLE_DEFINITIONS),
			set(frappe.get_all("Role", filters={"name": ["in", list(ROLE_DEFINITIONS)]}, pluck="name")),
		)
		self.assertEqual(frappe.db.get_value("Role", "Institution Super Admin", "two_factor_auth"), 1)
		self.assertEqual(frappe.db.get_value("Role", "Platform Super Admin", "two_factor_auth"), 1)
		self.assertEqual(frappe.db.get_value("Role", "System Manager", "two_factor_auth"), 1)
		self.assertEqual(frappe.db.get_value("Role", "Applicant", "desk_access"), 0)
		self.assertEqual(frappe.db.get_value("Role", "Student", "desk_access"), 0)

	def test_foundation_changes_create_append_only_audit_events(self):
		campus = frappe.get_doc(
			{
				"doctype": "Campus",
				"campus_code": "audit-campus",
				"campus_name": "Audit Campus",
				"institution": self.institution,
			}
		).insert()
		campus.campus_name = "Updated Audit Campus"
		campus.save()

		events = frappe.get_all(
			"Domain Audit Event",
			filters={"resource_type": "Campus", "resource_name": campus.name},
			fields=["name", "action", "previous_values", "resulting_values"],
			order_by="event_timestamp asc",
		)
		self.assertEqual([event.action for event in events], ["Created", "Updated"])
		self.assertEqual(frappe.parse_json(events[1].previous_values).campus_name, "Audit Campus")
		self.assertEqual(frappe.parse_json(events[1].resulting_values).campus_name, "Updated Audit Campus")

		event = frappe.get_doc("Domain Audit Event", events[0].name)
		event.action = "Changed"
		with self.assertRaises(frappe.ValidationError):
			event.save()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Domain Audit Event", event.name)

		frappe.delete_doc("Campus", campus.name)
		self.assertTrue(
			frappe.db.exists(
				"Domain Audit Event",
				{"resource_type": "Campus", "resource_name": campus.name, "action": "Deleted"},
			)
		)

	def test_foundation_permissions_follow_least_privilege(self):
		registry = self._user("registry-security@example.com", "Registry Officer")
		frappe.set_user(registry.name)
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertTrue(frappe.has_permission("Institution", "read"))
		self.assertFalse(frappe.has_permission("Institution", "write"))
		self.assertFalse(frappe.has_permission("Domain Audit Event", "read"))

	def test_institution_domain_is_normalised_and_validated(self):
		institution = frappe.get_doc("Institution", self.institution)
		institution.primary_domain = "https://college.example"
		with self.assertRaises(frappe.ValidationError):
			institution.save()

		institution.reload()
		institution.primary_domain = "College.Example."
		institution.save()
		self.assertEqual(institution.primary_domain, "college.example")

	def test_privileged_mfa_configuration_is_role_scoped(self):
		enable_privileged_mfa()
		self.assertEqual(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"), 1)
		self.assertEqual(frappe.db.get_value("Role", "All", "two_factor_auth"), 0)
		for role in ("System Manager", "Platform Super Admin", "Institution Super Admin"):
			self.assertEqual(frappe.db.get_value("Role", role, "two_factor_auth"), 1)

	def test_staff_suspension_requires_user_access_to_be_revoked(self):
		user = self._user("staff-security@example.com", "Registry Officer")
		staff = frappe.get_doc(
			{
				"doctype": "Staff Profile",
				"staff_number": "staff-security-001",
				"user": user.name,
				"institution": self.institution,
				"designation": "Registry Officer",
			}
		).insert()

		staff.employment_status = "Suspended"
		with self.assertRaises(frappe.ValidationError):
			staff.save()

		user.enabled = 0
		user.save()
		staff.reload()
		staff.employment_status = "Suspended"
		staff.save()
		self.assertEqual(staff.employment_status, "Suspended")

	@staticmethod
	def _user(email, role):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Security",
				"last_name": "Test",
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
