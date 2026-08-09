import frappe
from frappe.tests import IntegrationTestCase


class TestInstallation(IntegrationTestCase):
	def test_app_is_installed(self):
		self.assertIn("college_management", frappe.get_installed_apps())
