from pathlib import Path

from frappe.tests import UnitTestCase

APP_ROOT = Path(__file__).resolve().parents[1]


class TestApplicantPortalUI(UnitTestCase):
	def test_applications_page_exposes_manageable_application_records(self):
		template = (APP_ROOT / "www" / "admissions.html").read_text()
		script = (APP_ROOT / "www" / "admissions.js").read_text()
		self.assertIn('data-application-card', template)
		self.assertIn('data-application-search', template)
		self.assertIn('data-application-status', template)
		self.assertIn('cm-progress-track', template)
		self.assertNotIn('Available programmes', template)
		self.assertNotIn('Applications are saved automatically', template)
		self.assertEqual(template.count('href="{{ application.url | e }}"'), 1)
		self.assertIn('search.addEventListener("input", filterApplications)', script)
		self.assertIn('status.addEventListener("change", filterApplications)', script)

	def test_applicant_home_exposes_profile_details(self):
		template = (APP_ROOT / "www" / "applicant.html").read_text()
		components = (
			APP_ROOT / "templates" / "includes" / "applicant_portal" / "components.html"
		).read_text()
		self.assertIn('data-applicant-portal', template)
		self.assertIn("Applicant number", template)
		self.assertIn("Contact email", template)
		self.assertIn("institution.logo", components)
		self.assertIn('href="/admissions"', template)

	def test_applicant_home_has_responsive_component_structure(self):
		template = (APP_ROOT / "www" / "applicant.html").read_text()
		styles = (APP_ROOT / "www" / "applicant.css").read_text()
		portal_styles = (APP_ROOT / "public" / "css" / "applicant_portal.css").read_text()
		components = (
			APP_ROOT / "templates" / "includes" / "applicant_portal" / "components.html"
		).read_text()
		self.assertIn("cm-dashboard-grid", template)
		self.assertIn("portal_sidebar", template)
		self.assertIn("macro detail", components)
		self.assertIn("macro portal_sidebar", components)
		self.assertIn("grid-template-columns: 1.5rem minmax(0, 1fr)", portal_styles)
		self.assertNotIn("border-left-color", portal_styles)
		self.assertNotIn("border-bottom-color", portal_styles)
		self.assertIn("@media (max-width: 991px)", portal_styles)
		self.assertIn("@media (max-width: 991px)", styles)
		self.assertIn("@media (max-width: 575px)", styles)

	def test_draft_workspace_has_guided_step_rail_contract(self):
		"""A regression must not turn the resumable workspace back into an inline form."""
		template = (APP_ROOT / "www" / "admission.html").read_text()
		self.assertIn('data-portal-application', template)
		self.assertIn('data-step-progress', template)
		self.assertIn('data-step-state', template)
		self.assertIn('aria-current="{{ \'step\' if loop.first else \'false\' }}"', template)
		self.assertIn('data-save-status', template)
		self.assertIn('data-action="save-exit"', template)
		self.assertIn('cm-application-overview', template)
		self.assertIn('step.type == "Programme Selection"', template)
		self.assertIn('cm-programme-grid', template)
		self.assertIn('data-programme-selection', template)
		self.assertNotIn('cm-application-summary', template)
		self.assertIn('portal_sidebar', template)

	def test_workspace_styles_support_desktop_rail_and_mobile_progress_strip(self):
		"""A regression must not hide navigation or make it unusable on small screens."""
		styles = (APP_ROOT / "www" / "admission.css").read_text()
		self.assertIn('.cm-application-progress', styles)
		self.assertIn('.cm-step-navigation [data-step-state="complete"]', styles)
		self.assertIn('@media (max-width: 991px)', styles)
		self.assertIn('overflow-x: auto', styles)
		self.assertIn('grid-template-columns: 15rem minmax(0, 1fr)', styles)

	def test_completed_step_marker_receives_the_same_state_as_its_label(self):
		"""Changing a step must expose its completion state to the marker selector."""
		script = (APP_ROOT / "www" / "admission.js").read_text()
		self.assertIn("button.dataset.stepState = complete", script)
