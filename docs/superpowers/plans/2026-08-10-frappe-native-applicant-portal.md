# Frappe-Native Applicant Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the applicant dashboard and application workspace using Frappe-native portal, form, status, and responsive-layout conventions while preserving the governed admissions lifecycle.

**Architecture:** Keep Frappe website routes and server-rendered Jinja templates as the presentation boundary. Build page context from owner-scoped Python handlers, use Frappe controls and CSS tokens in the browser, and retain the existing whitelisted domain actions for saving, payment, submission, decisions, and offer responses. No new frontend framework, component library, or API layer is introduced.

**Tech Stack:** Frappe Framework 16.30.0, Python 3.14, Jinja, Frappe website JavaScript, Bootstrap/Frappe utility classes, CSS variables, Frappe integration tests, local in-app browser verification.

## Global Constraints

- Use Frappe Framework `v16.30.0`; do not patch Frappe core.
- Use Frappe's standard website template, portal conventions, controls, buttons, cards, alerts, indicators, spacing, and CSS variables.
- Keep institution-specific presentation limited to configured identity such as institution name, logo, and supported theme colour.
- Do not add a frontend framework, component library, icon pack, gradient, hero system, or third-party UI dependency.
- Preserve server-side ownership, permission, payment verification, submission, review, decision, acceptance, and student-conversion rules.
- Keep custom CSS limited to route layout and responsive step navigation.
- Keep all applicant-visible text translatable.
- Preserve keyboard operation, visible focus, semantic headings, explicit labels, status announcements, and mobile usability.
- Do not redesign staff Desk screens or create/push the future remote repository in this plan.

---

## File Structure

- `college_management/www/admissions.py`: owner-scoped dashboard context and applicant-profile save endpoint.
- `college_management/www/admissions.html`: Frappe-native dashboard markup.
- `college_management/www/admissions.css`: dashboard-only layout rules that Frappe utilities do not cover.
- `college_management/www/admissions.js`: start-application action and duplicate-action protection.
- `college_management/www/admission.py`: owner-scoped single-application context and configured/default step assembly.
- `college_management/www/admission.html`: draft wizard and submitted-application presentation.
- `college_management/www/admission.css`: application layout, step navigation, and review-list responsiveness.
- `college_management/www/admission.js`: Frappe controls, autosave, navigation, attachments, payment, submission, and offer actions.
- `college_management/templates/includes/application_field.html`: configured application-field rendering.
- `college_management/templates/includes/applicant_profile_field.html`: applicant-profile field rendering.
- `college_management/tests/test_applicant_submission.py`: server-context, ownership, step, autosave, payment, and lifecycle integration coverage.
- `college_management/tests/test_applicant_portal_ui.py`: small static contract test for framework-native markup and forbidden presentation patterns.
- `docs/increment-2-admissions-review-and-onboarding.md`: operator-facing description and smoke test.

---

### Task 1: Lock the owner-scoped portal context contract

**Files:**
- Modify: `college_management/tests/test_applicant_submission.py:114-195`
- Modify: `college_management/www/admissions.py:1-230`
- Modify: `college_management/www/admission.py:1-40`
- Modify: `college_management/hooks.py:90-100`
- Modify: `college_management/college_management_system/doctype/admission_programme/admission_programme.py`
- Modify: `college_management/college_management_system/doctype/admission_programme/admission_programme.json`
- Modify: `college_management/college_management_system/doctype/admission_application_field/admission_application_field.json`
- Create: `college_management/college_management_system/doctype/admission_application_step/__init__.py`
- Create: `college_management/college_management_system/doctype/admission_application_step/admission_application_step.py`
- Create: `college_management/college_management_system/doctype/admission_application_step/admission_application_step.json`

**Interfaces:**
- Consumes: `create_application(admission_programme: str) -> dict`, current Applicant Profile ownership, Admission Programme fields, and Frappe `website_route_rules`.
- Produces: `_application_summary(name: str) -> frappe._dict`, `_application_card(name: str) -> frappe._dict`, `_application_steps(offering, fields) -> list[frappe._dict]`, `_profile_fields(profile_name: str) -> list[frappe._dict]`, and `save_applicant_profile(values: dict | str) -> dict`.

- [ ] **Step 1: Extend the failing context test**

Add assertions to `test_configurable_application_steps_and_profile_autosave` for ordered keys, step types, payment requirements, native route metadata, and supported profile fields:

```python
self.assertEqual([step.key for step in card.steps], ["bio", "education", "documents", "fee", "confirm"])
self.assertEqual([step.type for step in card.steps], [row["step_type"] for row in steps])
self.assertTrue(card.require_payment)
self.assertEqual(context.application_url, f"/admissions/{application}")
self.assertEqual(context.sidebar_items[0].group_items[0].route, "/admissions")
self.assertEqual({field.key for field in card.profile_fields}, {
	"first_name", "middle_name", "last_name", "date_of_birth", "gender", "phone",
	"nationality", "state_of_origin", "local_government_area", "address",
})
```

Add `test_default_application_steps_remain_complete`:

```python
def test_default_application_steps_remain_complete(self):
	offering = self._published_offering(
		application_fee=1000,
		require_payment_before_submission=1,
		application_fields=[
			self._field("school", "Previous School", "Data"),
			{**self._field("result", "Result", "Attachment"), "allowed_extensions": "pdf"},
		],
	)
	user, _ = self._applicant()
	frappe.set_user(user.name)
	application = create_application(offering.name)["application"]
	frappe.form_dict = frappe._dict(application=application)
	context = frappe._dict()
	get_application_context(context)
	self.assertEqual(
		[step.type for step in context.application.steps],
		["Applicant Details", "Application Fields", "Application Fields", "Payment", "Review & Submit"],
	)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests \
  --app college_management \
  --module college_management.tests.test_applicant_submission
```

Expected: the module FAILS in `test_configurable_application_steps_and_profile_autosave` because `application_url` is not yet present on the route context.

- [ ] **Step 3: Implement the minimal context contract**

In `college_management/www/admission.py`, set the canonical URL after the owner-scoped application is resolved:

```python
context.application = _application_card(application_name)
context.application_url = f"/admissions/{context.application.name}"
context.sidebar_items = _applicant_sidebar(context.application)
```

Keep `_application_steps` as the only configured/default sequence builder. Validate Admission Programme configuration so field steps reference an existing `Application Fields` step, exactly one `Review & Submit` step exists when custom steps are present, and a `Payment` step exists when verified payment is required.

- [ ] **Step 4: Run the focused module and verify GREEN**

Run:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests \
  --app college_management \
  --module college_management.tests.test_applicant_submission
```

Expected: all Applicant Submission integration tests PASS.

- [ ] **Step 5: Commit the context and configuration slice**

```bash
git add college_management/hooks.py \
  college_management/college_management_system/doctype/admission_application_field/admission_application_field.json \
  college_management/college_management_system/doctype/admission_programme/admission_programme.json \
  college_management/college_management_system/doctype/admission_programme/admission_programme.py \
  college_management/college_management_system/doctype/admission_application_step \
  college_management/www/admissions.py college_management/www/admission.py \
  college_management/tests/test_applicant_submission.py
git commit -m "feat: add configurable applicant portal steps"
```

---

### Task 2: Standardise the admissions dashboard on native portal primitives

**Files:**
- Create: `college_management/tests/test_applicant_portal_ui.py`
- Modify: `college_management/www/admissions.html:1-67`
- Modify: `college_management/www/admissions.css:1-20`
- Modify: `college_management/www/admissions.js`

**Interfaces:**
- Consumes: `context.profile`, `context.applications`, `context.offerings`, and `create_application(admission_programme)`.
- Produces: semantic dashboard sections marked by `data-portal-dashboard`, application links using `application.url`, and start buttons using `data-action="create"` and `data-offering`.

- [ ] **Step 1: Write the failing native-markup contract test**

Create `college_management/tests/test_applicant_portal_ui.py`:

```python
from pathlib import Path

from frappe.tests import UnitTestCase


APP_ROOT = Path(__file__).resolve().parents[1]


class TestApplicantPortalUI(UnitTestCase):
	def test_dashboard_uses_frappe_portal_primitives(self):
		template = (APP_ROOT / "www" / "admissions.html").read_text()
		self.assertIn('data-portal-dashboard', template)
		self.assertIn('class="portal-container', template)
		self.assertIn('class="portal-section', template)
		self.assertIn("indicator-pill", template)
		self.assertIn("btn btn-primary", template)

	def test_portal_styles_do_not_define_a_parallel_design_system(self):
		styles = "\n".join(
			(APP_ROOT / "www" / filename).read_text()
			for filename in ("admissions.css", "admission.css")
		)
		for forbidden in ("linear-gradient", "@keyframes", "font-family:", "box-shadow:"):
			self.assertNotIn(forbidden, styles)
```

- [ ] **Step 2: Run the UI contract test and verify RED**

Run:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests \
  --app college_management \
  --module college_management.tests.test_applicant_portal_ui
```

Expected: FAIL because the dashboard does not yet use `portal-container`, `portal-section`, or `data-portal-dashboard`, and its CSS still defines hover shadow behaviour.

- [ ] **Step 3: Replace custom dashboard presentation with native markup**

Use one native portal container and native sections:

```html
<div class="portal-container" data-portal-dashboard>
	<section class="portal-section" aria-labelledby="your-applications">
		<div class="section-head">
			<h2 class="h4" id="your-applications">{{ _("Your applications") }}</h2>
			<p class="text-muted">{{ _("Continue an application or review its current status.") }}</p>
		</div>
		<!-- existing owner-scoped application cards -->
	</section>
	<section class="portal-section" aria-labelledby="available-programmes">
		<!-- existing published/open programme cards -->
	</section>
</div>
```

Retain standard `card`, `card-body`, `indicator-pill`, `btn-primary`, `btn-default`, grid, spacing, and text utility classes. Remove the custom hover transition and shadow. Keep only the dashboard max-width and small-screen identity-card width when the framework utilities cannot express them.

In `admissions.js`, disable the selected start button while `create_application` is pending and restore it on failure so duplicate clicks cannot create parallel requests.

- [ ] **Step 4: Run UI and Applicant Submission tests and verify GREEN**

Run:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management \
  --module college_management.tests.test_applicant_portal_ui

./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management \
  --module college_management.tests.test_applicant_submission
```

Expected: both modules PASS.

- [ ] **Step 5: Commit the dashboard slice**

```bash
git add college_management/tests/test_applicant_portal_ui.py \
  college_management/www/admissions.html \
  college_management/www/admissions.css \
  college_management/www/admissions.js
git commit -m "feat: standardize applicant dashboard UI"
```

---

### Task 3: Standardise draft form controls, navigation, autosave, and attachments

**Files:**
- Modify: `college_management/tests/test_applicant_portal_ui.py`
- Modify: `college_management/templates/includes/application_field.html`
- Modify: `college_management/templates/includes/applicant_profile_field.html`
- Modify: `college_management/www/admission.html:1-61`
- Modify: `college_management/www/admission.css:1-75`
- Modify: `college_management/www/admission.js:1-244`

**Interfaces:**
- Consumes: `application.steps`, `application.profile_fields`, `application.fields`, Frappe `frappe.ui.form.make_control`, `save_applicant_profile(values)`, `save_application_responses(application, responses)`, and `/api/method/upload_file`.
- Produces: step controls with `data-step-target`, panels with `data-step`, live save state via `data-save-status`, and private file values via `data-current`.

- [ ] **Step 1: Extend the failing UI contract**

Add:

```python
def test_application_workspace_exposes_accessible_native_states(self):
	template = (APP_ROOT / "www" / "admission.html").read_text()
	self.assertIn('data-portal-application', template)
	self.assertIn('aria-current="{{ \'step\' if loop.first else \'false\' }}"', template)
	self.assertIn('aria-live="polite"', template)
	self.assertIn('class="alert alert-danger', template)
	self.assertIn('class="btn btn-default', template)
	self.assertIn('class="btn btn-primary', template)

def test_application_fields_use_framework_controls_and_labels(self):
	application_field = (APP_ROOT / "templates" / "includes" / "application_field.html").read_text()
	profile_field = (APP_ROOT / "templates" / "includes" / "applicant_profile_field.html").read_text()
	self.assertIn("data-frappe-control", application_field)
	self.assertIn("data-frappe-control", profile_field)
	self.assertIn("form-control", application_field)
	self.assertIn("form-control", profile_field)
```

- [ ] **Step 2: Run the UI contract and verify RED**

Run the `test_applicant_portal_ui` module. Expected: FAIL because `data-portal-application`, `aria-live="polite"`, and the persistent error alert are absent.

- [ ] **Step 3: Implement native draft-workspace states**

Add the route marker and one initially hidden native error alert:

```html
<form data-application-form="{{ application.name | e }}" data-portal-application novalidate>
	<div class="alert alert-danger d-none" role="alert" data-portal-error></div>
	<!-- native step navigation and panels -->
	<span class="small text-muted mr-auto" data-save-status role="status" aria-live="polite">
		{{ _("All changes saved") }}
	</span>
</form>
```

Keep Frappe controls for Date and Link fields and standard labelled Bootstrap/Frappe controls for Data, Small Text, Select, Check, and Attachment. Preserve configured help text and allowed file extensions.

In `admission.js`:

- initialise Frappe controls once per wrapper;
- serialize only whitelisted profile and configured response fields;
- queue autosaves per form;
- show `Saving…`, `All changes saved`, or the native error alert;
- do not advance when validation or saving fails;
- disable only the clicked navigation/action button while pending;
- upload files privately against the owned Admission Application; and
- update the final review summary after every successful save.

Use one error presenter:

```javascript
function show_portal_error(form, message = "") {
	const alert = form.querySelector("[data-portal-error]");
	alert.textContent = message;
	alert.classList.toggle("d-none", !message);
}
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the UI contract and Applicant Submission modules. Expected: both PASS.

- [ ] **Step 5: Commit the draft-workspace slice**

```bash
git add college_management/tests/test_applicant_portal_ui.py \
  college_management/templates/includes/application_field.html \
  college_management/templates/includes/applicant_profile_field.html \
  college_management/www/admission.html \
  college_management/www/admission.css \
  college_management/www/admission.js
git commit -m "feat: standardize applicant form workflow"
```

---

### Task 4: Standardise payment, submitted application, decision, and offer states

**Files:**
- Modify: `college_management/tests/test_applicant_submission.py`
- Modify: `college_management/tests/test_applicant_portal_ui.py`
- Modify: `college_management/www/admission.py`
- Modify: `college_management/www/admission.html:62-75`
- Modify: `college_management/www/admission.js`

**Interfaces:**
- Consumes: `application.invoice`, `application.transaction`, `application.decision`, `application.letter`, `application.student`, `create_application_invoice`, `initialize_payment`, `verify_payment`, `submit_application`, and `respond_to_admission`.
- Produces: applicant-visible read-only summary, native payment/decision/offer status cards, and reload-after-success browser actions.

- [ ] **Step 1: Write failing visibility and markup assertions**

In `test_portal_context_and_response_action_are_owner_scoped`, assert that submitted context exposes applicant answers and applicant-visible outcome data but not internal reviews:

```python
self.assertFalse(hasattr(application_context.application, "reviews"))
self.assertFalse(hasattr(application_context.application, "review_summary"))
self.assertEqual(application_context.application.fields[0].value, "Applicant")
```

Extend the UI contract:

```python
def test_submitted_workspace_uses_native_status_components(self):
	template = (APP_ROOT / "www" / "admission.html").read_text()
	self.assertIn('data-submitted-workspace', template)
	for text in (
		"Submitted application", "Application fee", "Admission decision",
		"Admission letter", "Student onboarding complete",
	):
		self.assertIn(text, template)
	self.assertIn("indicator-pill", template)
	self.assertIn("alert alert-success", template)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run both focused modules. Expected: the UI contract FAILS because `data-submitted-workspace` is not yet present. The server visibility assertions must already pass; if they fail, remove the internal data from `_application_card` before continuing.

- [ ] **Step 3: Implement the native state presentation**

Mark the submitted container with `data-submitted-workspace`. Render the submitted answer summary in the main column and use standard cards in the secondary column for:

- no-fee, invoice-required, pending-payment, verified-payment, and reconciliation states;
- awaiting-decision, admitted, and non-admitted outcomes;
- admission-letter availability and response state; and
- completed student conversion.

Use `btn-primary` only for the next recommended action. Use `btn-default` for viewing documents and declining an offer. Keep applicant-visible decision reason only; do not include review data in the route context or template.

In `admission.js`, protect action buttons against duplicate calls and reload after authoritative server success. Payment initialization may navigate only to the server-returned provider URL.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Applicant Submission and Applicant Portal UI modules. Expected: both PASS.

- [ ] **Step 5: Commit the submitted-state slice**

```bash
git add college_management/tests/test_applicant_submission.py \
  college_management/tests/test_applicant_portal_ui.py \
  college_management/www/admission.py \
  college_management/www/admission.html \
  college_management/www/admission.js
git commit -m "feat: standardize applicant status views"
```

---

### Task 5: Verify desktop/mobile behavior and finish documentation

**Files:**
- Modify: `docs/increment-2-admissions-review-and-onboarding.md`
- Modify only if verification reveals a defect: applicant portal files from Tasks 1-4.

**Interfaces:**
- Consumes: the completed `/admissions` and `/admissions/<application-id>` routes and the local `college.localhost` site.
- Produces: verified applicant portal, current operator documentation, and a clean commit series ready for repository creation.

- [ ] **Step 1: Migrate the site and run the full integration suite**

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost migrate

./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management
```

Expected: migration exits 0 and all integration tests PASS. The documented Frappe `duckdb_sync.cleanup_old_syncs` baseline warning may appear; no additional warning is accepted.

- [ ] **Step 2: Exercise the applicant journey in the local browser**

Using an Applicant user and a published programme:

1. Open `/admissions` and verify native dashboard hierarchy, status indicators, programme cards, and empty states.
2. Start an application and confirm navigation to `/admissions/<application-id>`.
3. Complete Applicant Details and configured fields; verify saving, saved, and failed states.
4. Upload an allowed private document and verify the existing-document link after reload.
5. Verify payment-required state prevents submission until the server reports Paid.
6. Review and submit; verify fields become read-only.
7. Verify decision, letter, acceptance/decline, and student-conversion states with the available test records.
8. Confirm there are no browser console errors.

- [ ] **Step 3: Verify responsive and keyboard behavior**

At desktop width and at a mobile viewport near 390 × 844:

- confirm the dashboard remains one readable column when required;
- confirm step navigation scrolls horizontally without covering the form;
- tab through every visible field and action;
- confirm focus remains visible;
- confirm Back, Save and continue, Submit application, payment, and offer buttons are reachable; and
- confirm review rows collapse to one column on mobile.

- [ ] **Step 4: Update operator documentation**

Update `docs/increment-2-admissions-review-and-onboarding.md` so the User Interfaces and Operator Smoke Test sections match the verified routes, configured/default steps, autosave states, native Frappe controls, submitted summary, and mobile behavior.

- [ ] **Step 5: Run final static verification**

```bash
ruff check college_management
git diff --check
git status --short
```

Expected: Ruff reports `All checks passed!`, `git diff --check` emits no errors, and status contains only intentional portal/documentation changes.

- [ ] **Step 6: Commit final verification/documentation fixes**

```bash
git add docs/increment-2-admissions-review-and-onboarding.md
git add college_management/www college_management/templates college_management/tests \
  college_management/hooks.py college_management/college_management_system/doctype
git commit -m "docs: record completed applicant portal"
```

- [ ] **Step 7: Record the repository handoff**

After the final commit, report:

- the final commit range;
- full test count and result;
- migration, Ruff, diff, browser, desktop, mobile, and keyboard verification results;
- any known Frappe baseline warning; and
- that creating the new remote repository and pushing remains the next explicit operation.
