import frappe
from frappe.utils import get_datetime, getdate

from college_management.college_management_system.doctype.base import CodeDocument, in_schema_operation


class AdmissionCycle(CodeDocument):
	code_field = "admission_cycle_code"

	def validate(self):
		super().validate()
		previous = self.get_doc_before_save()
		self._validate_window()
		self._validate_status(previous)
		if previous and previous.status in {"Published", "Closed", "Archived"}:
			self._validate_immutable_configuration(previous)

	def on_trash(self):
		if not in_schema_operation() and self.status != "Draft":
			frappe.throw(frappe._("Only a Draft Admission Cycle can be deleted."))

	def _validate_window(self):
		if get_datetime(self.applications_close_at) <= get_datetime(self.applications_open_from):
			frappe.throw(frappe._("Applications Close At must be after Applications Open From."))
		if self.decision_deadline and getdate(self.decision_deadline) < getdate(self.applications_close_at):
			frappe.throw(frappe._("Decision Deadline cannot be before the application closing date."))

	def _validate_status(self, previous):
		if not previous:
			if self.status != "Draft":
				frappe.throw(frappe._("An Admission Cycle must be created as Draft."))
			return

		allowed = {
			"Draft": {"Draft", "Under Review"},
			"Under Review": {"Draft", "Under Review", "Published"},
			"Published": {"Published", "Closed"},
			"Closed": {"Closed", "Archived"},
			"Archived": {"Archived"},
		}
		if self.status not in allowed[previous.status]:
			frappe.throw(
				frappe._("Admission Cycle status cannot change from {0} to {1}.").format(
					previous.status, self.status
				)
			)

		if self.status == "Published" and previous.status != "Published":
			self._require_publisher()
			if not frappe.db.exists("Admission Programme", {"admission_cycle": self.name, "is_enabled": 1}):
				frappe.throw(
					frappe._("Add at least one enabled Admission Programme before publishing the cycle.")
				)

	@staticmethod
	def _require_publisher():
		if frappe.session.user == "Administrator":
			return
		if not {"System Manager", "Institution Super Admin"}.intersection(frappe.get_roles()):
			frappe.throw(
				frappe._("Only a System Manager or Institution Super Admin can publish an Admission Cycle."),
				frappe.PermissionError,
			)

	def _validate_immutable_configuration(self, previous):
		fields = (
			"cycle_name",
			"academic_session",
			"applications_open_from",
			"applications_close_at",
			"decision_deadline",
			"notes",
		)
		if any(self.get(field) != previous.get(field) for field in fields):
			frappe.throw(frappe._("A Published, Closed, or Archived Admission Cycle cannot be changed."))
