from pathlib import Path

from frappe.tests import UnitTestCase

APP_ROOT = Path(__file__).resolve().parents[1]


class TestApplicantPortalUI(UnitTestCase):
	def test_applications_page_uses_tables_instead_of_record_cards(self):
		template = (APP_ROOT / "www" / "admissions.html").read_text()
		self.assertIn('data-applications-table', template)
		self.assertIn('class="table', template)
		self.assertNotIn("cm-record-card", template)
		self.assertNotIn("cm-programme-card", template)

	def test_applicant_home_exposes_profile_details(self):
		template = (APP_ROOT / "www" / "applicant.html").read_text()
		self.assertIn('data-applicant-home', template)
		self.assertIn("Applicant number", template)
		self.assertIn("Contact email", template)
		self.assertIn('href="/admissions"', template)

	def test_draft_workspace_has_guided_step_rail_contract(self):
		"""A regression must not turn the resumable workspace back into an inline form."""
		template = (APP_ROOT / "www" / "admission.html").read_text()
		self.assertIn('data-portal-application', template)
		self.assertIn('data-step-progress', template)
		self.assertIn('data-step-state', template)
		self.assertIn('aria-current="{{ \'step\' if loop.first else \'false\' }}"', template)
		self.assertIn('data-save-status', template)
		self.assertIn('data-action="save-exit"', template)

	def test_workspace_styles_support_desktop_rail_and_mobile_progress_strip(self):
		"""A regression must not hide navigation or make it unusable on small screens."""
		styles = (APP_ROOT / "www" / "admission.css").read_text()
		self.assertIn('.cm-application-progress', styles)
		self.assertIn('.cm-step-navigation [data-step-state="complete"]', styles)
		self.assertIn('@media (max-width: 991px)', styles)
		self.assertIn('overflow-x: auto', styles)

	def test_completed_step_marker_receives_the_same_state_as_its_label(self):
		"""Changing a step must expose its completion state to the marker selector."""
		script = (APP_ROOT / "www" / "admission.js").read_text()
		self.assertIn("button.dataset.stepState = complete", script)
