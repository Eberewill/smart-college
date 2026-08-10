import frappe
from frappe.utils import getdate

from college_management.college_management_system.doctype.base import CodeDocument, in_schema_operation


class StaffProfile(CodeDocument):
	code_field = "staff_number"

	def before_validate(self):
		if not self.institution:
			self.institution = frappe.db.get_value("Institution", {}, "name")

	def validate(self):
		super().validate()
		self._validate_user()
		self._validate_organisation()
		self._validate_status_transition()

	def on_trash(self):
		if not in_schema_operation():
			frappe.throw(frappe._("Staff Profiles cannot be deleted. Set the Employment Status to Archived."))

	def _validate_user(self):
		if self.user in {"Administrator", "Guest"}:
			frappe.throw(frappe._("Standard platform accounts cannot have a Staff Profile."))

		enabled, user_type = frappe.db.get_value("User", self.user, ["enabled", "user_type"])
		if user_type != "System User":
			frappe.throw(frappe._("A Staff Profile must be linked to a System User."))
		if self.employment_status == "Active" and not enabled:
			frappe.throw(frappe._("Enable the linked User before marking this Staff Profile Active."))
		if self.employment_status in {"Suspended", "Separated", "Archived"} and enabled:
			frappe.throw(
				frappe._("Disable the linked User to revoke access before setting this Employment Status.")
			)

	def _validate_organisation(self):
		if (
			self.primary_campus
			and frappe.db.get_value("Campus", self.primary_campus, "institution") != self.institution
		):
			frappe.throw(frappe._("Primary Campus must belong to the selected Institution."))

		if self.primary_department:
			department_faculty = frappe.db.get_value("Department", self.primary_department, "faculty")
			if self.primary_faculty and self.primary_faculty != department_faculty:
				frappe.throw(frappe._("Primary Department must belong to the selected Faculty."))
			self.primary_faculty = department_faculty

		if (
			self.primary_faculty
			and frappe.db.get_value("Faculty", self.primary_faculty, "institution") != self.institution
		):
			frappe.throw(frappe._("Primary Faculty must belong to the selected Institution."))

		if self.appointment_date and getdate(self.appointment_date) > getdate():
			frappe.throw(frappe._("Appointment Date cannot be in the future."))

	def _validate_status_transition(self):
		previous = self.get_doc_before_save()
		if not previous:
			return
		allowed = {
			"Active": {"Active", "On Leave", "Suspended", "Separated"},
			"On Leave": {"Active", "On Leave", "Suspended", "Separated"},
			"Suspended": {"Active", "Suspended", "Separated"},
			"Separated": {"Separated", "Archived"},
			"Archived": {"Archived"},
		}
		if self.employment_status not in allowed[previous.employment_status]:
			frappe.throw(
				frappe._("Employment Status cannot change from {0} to {1}.").format(
					previous.employment_status, self.employment_status
				)
			)
