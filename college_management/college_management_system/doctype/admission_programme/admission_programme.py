import re

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime

from college_management.college_management_system.doctype.base import in_schema_operation

FIELD_KEY_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
ATTACHMENT_TYPES = {"pdf", "jpg", "jpeg", "png"}


class AdmissionProgramme(Document):
	def validate(self):
		self._validate_cycle_is_configurable()
		self._validate_unique_offering()
		self._validate_programme_and_campus()
		self._validate_window()
		self._validate_fee()
		self._validate_application_fields()

	def on_trash(self):
		if not in_schema_operation():
			self._validate_cycle_is_configurable()

	def _validate_cycle_is_configurable(self):
		status = frappe.db.get_value("Admission Cycle", self.admission_cycle, "status")
		if status not in {"Draft", "Under Review"}:
			frappe.throw(frappe._("Admission Programmes cannot be changed after their cycle is published."))

	def _validate_unique_offering(self):
		offerings = frappe.get_all(
			"Admission Programme",
			filters={"admission_cycle": self.admission_cycle, "programme": self.programme},
			fields=("name", "campus"),
		)
		if any(row.name != self.name and (row.campus or "") == (self.campus or "") for row in offerings):
			frappe.throw(frappe._("This programme and campus are already offered in the cycle."))

	def _validate_programme_and_campus(self):
		if not frappe.db.get_value("Programme", self.programme, "is_active"):
			frappe.throw(frappe._("Only an active Programme can be offered for admission."))
		if self.campus and not frappe.db.get_value("Campus", self.campus, "is_active"):
			frappe.throw(frappe._("Only an active Campus can be used for admission."))
		if cint(self.capacity) < 0:
			frappe.throw(frappe._("Available Places cannot be negative."))

	def _validate_window(self):
		cycle_open, cycle_close = frappe.db.get_value(
			"Admission Cycle",
			self.admission_cycle,
			["applications_open_from", "applications_close_at"],
		)
		opening = get_datetime(self.applications_open_from or cycle_open)
		closing = get_datetime(self.applications_close_at or cycle_close)
		if closing <= opening:
			frappe.throw(frappe._("The programme closing time must be after its opening time."))
		if opening < get_datetime(cycle_open) or closing > get_datetime(cycle_close):
			frappe.throw(
				frappe._("A programme application window must stay within its Admission Cycle window.")
			)

	def _validate_fee(self):
		if flt(self.application_fee) < 0:
			frappe.throw(frappe._("Application Fee cannot be negative."))
		if self.require_payment_before_submission and not flt(self.application_fee):
			frappe.throw(
				frappe._("A positive Application Fee is required when payment is required before submission.")
			)

	def _validate_application_fields(self):
		seen = set()
		for row in self.application_fields:
			row.field_key = (row.field_key or "").strip().lower()
			if not FIELD_KEY_PATTERN.fullmatch(row.field_key):
				frappe.throw(
					frappe._("Field Key {0} must use lowercase letters, numbers, and underscores.").format(
						row.field_key
					)
				)
			if row.field_key in seen:
				frappe.throw(frappe._("Application Field {0} is duplicated.").format(row.field_key))
			seen.add(row.field_key)
			if row.field_type == "Select" and not (row.options or "").strip():
				frappe.throw(frappe._("Select field {0} requires options.").format(row.field_key))
			if row.field_type == "Attachment":
				self._validate_attachment_field(row)

	@staticmethod
	def _validate_attachment_field(row):
		extensions = {
			extension.strip().lower().lstrip(".")
			for extension in (row.allowed_extensions or "").split(",")
			if extension.strip()
		}
		if not extensions or not extensions.issubset(ATTACHMENT_TYPES):
			frappe.throw(
				frappe._("Attachment field {0} may allow only PDF, JPG, JPEG, or PNG files.").format(
					row.field_key
				)
			)
		if flt(row.maximum_file_size_mb) <= 0 or flt(row.maximum_file_size_mb) > 25:
			frappe.throw(
				frappe._("Attachment field {0} must have a file size limit from 1 to 25 MB.").format(
					row.field_key
				)
			)
		row.allowed_extensions = ",".join(sorted(extensions))
