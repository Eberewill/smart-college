from college_management.college_management_system.doctype.base import CodeDocument, validate_date_range


class AcademicSession(CodeDocument):
	code_field = "session_code"

	def validate(self):
		super().validate()
		validate_date_range(self, "start_date", "end_date")
