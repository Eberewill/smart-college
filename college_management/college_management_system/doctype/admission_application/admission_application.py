from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, get_datetime, getdate, now_datetime

from college_management.college_management_system.doctype.base import in_schema_operation

FILE_SIGNATURES = {
	"jpeg": (b"\xff\xd8\xff",),
	"jpg": (b"\xff\xd8\xff",),
	"pdf": (b"%PDF-",),
	"png": (b"\x89PNG\r\n\x1a\n",),
}


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return True
	if ptype == "write" and _is_submission_action(doc):
		return True
	if doc.is_new() and ptype == "create":
		return True
	if "Applicant" in roles and doc.owner != user:
		return False
	if (
		"Applicant" in roles
		and ptype in {"write", "delete"}
		and frappe.db.get_value("Admission Application", doc.name, "status") == "Submitted"
	):
		return False
	return True


def _is_submission_action(doc):
	return getattr(frappe.flags, "admission_submission", None) == doc.name


def has_file_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	if (
		doc.attached_to_doctype == "Admission Application"
		and ptype in {"write", "delete"}
		and frappe.db.get_value("Admission Application", doc.attached_to_name, "status") == "Submitted"
	):
		return False
	return True


def protect_submitted_application_file(doc, method=None):
	if (
		doc.attached_to_doctype == "Admission Application"
		and frappe.db.get_value("Admission Application", doc.attached_to_name, "status") == "Submitted"
		and frappe.session.user != "Administrator"
		and "System Manager" not in frappe.get_roles()
	):
		frappe.throw(
			frappe._("Files attached to a submitted application cannot be changed or deleted."),
			frappe.PermissionError,
		)


class AdmissionApplication(Document):
	def before_naming(self):
		series = frappe.db.get_value("Institution", {}, "application_number_series")
		self.application_number = make_autoname(series)

	def before_validate(self):
		if self.is_new():
			self.owner = frappe.db.get_value("Applicant Profile", self.applicant_profile, "user")

	def validate(self):
		previous = self.get_doc_before_save()
		self._validate_identity(previous)
		self._validate_unique_application()
		if previous and previous.status == "Submitted":
			frappe.throw(frappe._("A submitted application is immutable."))
		if self.status != "Draft" and not _is_submission_action(self):
			frappe.throw(frappe._("Use the secure submission action to submit an application."))

		offering = self._get_open_offering()
		self.admission_cycle = offering.admission_cycle
		self.programme = offering.programme
		self._validate_responses(offering, require_complete=self.status == "Submitted")
		if self.status == "Submitted":
			if offering.require_payment_before_submission:
				frappe.throw(frappe._("Verified application-fee payment is required before submission."))
			self.submitted_at = now_datetime()
			self.submission_snapshot = self._submission_snapshot(offering)

	def on_trash(self):
		if not in_schema_operation() and self.status != "Draft":
			frappe.throw(frappe._("Only a Draft application can be deleted."))

	def _validate_identity(self, previous):
		profile = frappe.db.get_value(
			"Applicant Profile", self.applicant_profile, ["user", "status"], as_dict=True
		)
		if not profile or profile.status != "Active":
			frappe.throw(frappe._("An application requires an active Applicant Profile."))
		if "Applicant" in frappe.get_roles() and frappe.session.user != profile.user:
			frappe.throw(
				frappe._("Applicants can create and edit only their own applications."),
				frappe.PermissionError,
			)
		if previous and previous.applicant_profile != self.applicant_profile:
			frappe.throw(frappe._("Applicant Profile cannot be changed after creation."))
		if previous and previous.admission_programme != self.admission_programme:
			frappe.throw(frappe._("Admission Programme cannot be changed after creation."))
		if self.owner and self.owner != profile.user:
			frappe.throw(frappe._("Application ownership must match its Applicant Profile."))

	def _validate_unique_application(self):
		if frappe.db.exists(
			"Admission Application",
			{
				"applicant_profile": self.applicant_profile,
				"admission_programme": self.admission_programme,
				"name": ["!=", self.name or ""],
			},
		):
			frappe.throw(frappe._("This applicant already has an application for the programme."))

	def _get_open_offering(self):
		offering = frappe.get_doc("Admission Programme", self.admission_programme)
		cycle = frappe.db.get_value(
			"Admission Cycle",
			offering.admission_cycle,
			["status", "applications_open_from", "applications_close_at"],
			as_dict=True,
		)
		now = now_datetime()
		opening = get_datetime(offering.applications_open_from or cycle.applications_open_from)
		closing = get_datetime(offering.applications_close_at or cycle.applications_close_at)
		if not offering.is_enabled or cycle.status != "Published" or not opening <= now <= closing:
			frappe.throw(frappe._("This programme is not currently accepting applications."))
		return offering

	def _validate_responses(self, offering, require_complete):
		definitions = {row.field_key: row for row in offering.application_fields}
		seen = set()
		for row in self.responses:
			if row.field_key not in definitions:
				frappe.throw(frappe._("Application Field {0} is not configured.").format(row.field_key))
			if row.field_key in seen:
				frappe.throw(frappe._("Application Field {0} is duplicated.").format(row.field_key))
			seen.add(row.field_key)
			definition = definitions[row.field_key]
			row.field_label = definition.label
			self._validate_response(row, definition)

		if require_complete:
			missing = [
				definition.label
				for key, definition in definitions.items()
				if definition.is_required
				and (
					key not in seen
					or not self._response_has_value(
						next(row for row in self.responses if row.field_key == key), definition
					)
				)
			]
			if missing:
				frappe.throw(frappe._("Complete the required fields: {0}.").format(", ".join(missing)))

	def _validate_response(self, row, definition):
		value = (row.response_value or "").strip()
		if definition.field_type == "Attachment":
			if value:
				frappe.throw(frappe._("Attachment fields cannot contain a text response."))
			if row.attachment:
				self._validate_attachment(row.attachment, definition)
			return
		if row.attachment:
			frappe.throw(frappe._("Only an Attachment field can contain a file."))
		if not value:
			return
		if definition.field_type == "Data" and len(value) > 140:
			frappe.throw(frappe._("{0} cannot exceed 140 characters.").format(definition.label))
		if definition.field_type == "Small Text" and len(value) > 2000:
			frappe.throw(frappe._("{0} cannot exceed 2,000 characters.").format(definition.label))
		if definition.field_type == "Date":
			getdate(value)
		if definition.field_type == "Select" and value not in {
			option.strip() for option in definition.options.splitlines() if option.strip()
		}:
			frappe.throw(frappe._("{0} is not an allowed option for {1}.").format(value, definition.label))
		if definition.field_type == "Check" and value not in {"0", "1"}:
			frappe.throw(frappe._("{0} must be checked or unchecked.").format(definition.label))
		row.response_value = value

	def _validate_attachment(self, file_url, definition):
		file = frappe.get_doc("File", {"file_url": file_url})
		if (
			not file.is_private
			or file.owner != self.owner
			or file.attached_to_doctype != self.doctype
			or file.attached_to_name != self.name
		):
			frappe.throw(frappe._("Application attachments must be private and owned by this application."))
		extension = Path(file.file_name).suffix.lower().lstrip(".")
		allowed = {item.strip() for item in definition.allowed_extensions.split(",")}
		if extension not in allowed:
			frappe.throw(frappe._("The file type for {0} is not allowed.").format(definition.label))
		if cint(file.file_size) > definition.maximum_file_size_mb * 1024 * 1024:
			frappe.throw(frappe._("The file for {0} exceeds its size limit.").format(definition.label))
		content = file.get_content(encodings=[])
		if not any(content.startswith(signature) for signature in FILE_SIGNATURES[extension]):
			frappe.throw(
				frappe._("The file content for {0} does not match its extension.").format(definition.label)
			)

	@staticmethod
	def _response_has_value(response, definition):
		if definition.field_type == "Attachment":
			return bool(response.attachment)
		if definition.field_type == "Check":
			return response.response_value == "1"
		return bool((response.response_value or "").strip())

	def _submission_snapshot(self, offering):
		profile = frappe.get_doc("Applicant Profile", self.applicant_profile)
		return frappe.as_json(
			{
				"applicant": {
					"applicant_number": profile.applicant_number,
					"first_name": profile.first_name,
					"middle_name": profile.middle_name,
					"last_name": profile.last_name,
					"date_of_birth": profile.date_of_birth,
					"gender": profile.gender,
					"phone": profile.phone,
					"nationality": profile.nationality,
					"state_of_origin": profile.state_of_origin,
					"local_government_area": profile.local_government_area,
					"address": profile.address,
				},
				"offering": {
					"admission_cycle": offering.admission_cycle,
					"admission_programme": offering.name,
					"programme": offering.programme,
					"campus": offering.campus,
				},
				"responses": [
					{
						"field_key": row.field_key,
						"field_label": row.field_label,
						"response_value": row.response_value,
						"attachment": row.attachment,
					}
					for row in self.responses
				],
			},
			indent=2,
		)


@frappe.whitelist(methods=["POST"])
def create_application(admission_programme):
	profile = frappe.db.get_value("Applicant Profile", {"user": frappe.session.user}, "name")
	if not profile:
		frappe.throw(frappe._("An active Applicant Profile is required."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": "Admission Application",
			"applicant_profile": profile,
			"admission_programme": admission_programme,
		}
	).insert()
	return {"application": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def submit_application(application):
	doc = frappe.get_doc("Admission Application", application)
	doc.check_permission("write")
	if doc.status != "Draft":
		frappe.throw(frappe._("Only a Draft application can be submitted."))
	frappe.flags.admission_submission = doc.name
	try:
		doc.status = "Submitted"
		doc.save()
	finally:
		frappe.flags.admission_submission = None
	return {"application": doc.name, "status": doc.status, "submitted_at": doc.submitted_at}
