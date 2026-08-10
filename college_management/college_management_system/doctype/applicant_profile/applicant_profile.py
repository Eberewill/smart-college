import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, nowdate

from college_management.college_management_system.doctype.base import in_schema_operation


class ApplicantProfile(Document):
	def before_naming(self):
		series = frappe.db.get_value("Institution", {}, "applicant_number_series")
		self.applicant_number = make_autoname(series)

	def validate(self):
		previous = self.get_doc_before_save()
		user = frappe.db.get_value("User", self.user, ["user_type", "enabled"], as_dict=True)
		if not user or user.user_type != "Website User":
			frappe.throw(frappe._("An Applicant Profile must belong to a Website User."))
		if self.status == "Active" and not user.enabled:
			frappe.throw(frappe._("An active Applicant Profile requires an enabled User."))
		if self.date_of_birth and getdate(self.date_of_birth) >= getdate(nowdate()):
			frappe.throw(frappe._("Date of Birth must be in the past."))
		if previous and previous.user != self.user:
			frappe.throw(frappe._("The User on an Applicant Profile cannot be changed."))
		if previous and previous.applicant_number != self.applicant_number:
			frappe.throw(frappe._("Applicant Number cannot be changed."))
		if (
			previous
			and previous.status != self.status
			and frappe.session.user != "Administrator"
			and "System Manager" not in frappe.get_roles()
		):
			frappe.throw(frappe._("Only a System Manager can change Applicant Profile status."))

	def on_trash(self):
		if not in_schema_operation():
			frappe.throw(frappe._("Applicant Profiles cannot be deleted. Archive the profile instead."))
