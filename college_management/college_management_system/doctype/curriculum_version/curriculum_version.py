import frappe
from frappe.utils import cint, flt, getdate

from college_management.college_management_system.doctype.base import CodeDocument


class CurriculumVersion(CodeDocument):
	code_field = "curriculum_code"

	def validate(self):
		super().validate()
		previous = self.get_doc_before_save()
		self._validate_status(previous)
		self._validate_effective_sessions()
		self._validate_courses()
		self._validate_prerequisites()
		if previous and previous.status in {"Active", "Retired"}:
			self._validate_immutable_structure(previous)

	def _validate_status(self, previous):
		if not previous:
			if self.status != "Draft":
				frappe.throw(frappe._("A Curriculum Version must be created as Draft."))
			return

		allowed = {
			"Draft": {"Draft", "Under Review"},
			"Under Review": {"Draft", "Under Review", "Active"},
			"Active": {"Active", "Retired"},
			"Retired": {"Retired"},
		}
		if self.status not in allowed[previous.status]:
			frappe.throw(
				frappe._("Curriculum status cannot change from {0} to {1}.").format(
					previous.status, self.status
				)
			)
		if self.status == "Active" and not self.courses:
			frappe.throw(frappe._("An active curriculum must contain at least one course."))

	def _validate_effective_sessions(self):
		if not self.effective_to_session:
			return
		start = frappe.db.get_value("Academic Session", self.effective_from_session, "start_date")
		end = frappe.db.get_value("Academic Session", self.effective_to_session, "start_date")
		if getdate(end) < getdate(start):
			frappe.throw(frappe._("Effective To Session cannot precede Effective From Session."))

	def _validate_courses(self):
		duration = cint(frappe.db.get_value("Programme", self.programme, "duration_semesters"))
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(frappe._("Course {0} is listed more than once.").format(row.course))
			seen.add(row.course)
			if cint(row.semester_number) < 1 or cint(row.semester_number) > duration:
				frappe.throw(
					frappe._("Semester Number for {0} must be within the programme duration.").format(
						row.course
					)
				)
			if flt(row.credit_units) <= 0:
				frappe.throw(frappe._("Credit Units for {0} must be greater than zero.").format(row.course))

	def _validate_prerequisites(self):
		courses = {row.course for row in self.courses}
		edges = set()
		graph = {course: set() for course in courses}
		for row in self.prerequisites:
			edge = (row.course, row.prerequisite_course)
			if row.course not in courses or row.prerequisite_course not in courses:
				frappe.throw(frappe._("Prerequisite courses must both exist in this curriculum."))
			if row.course == row.prerequisite_course:
				frappe.throw(frappe._("A course cannot be its own prerequisite."))
			if edge in edges:
				frappe.throw(frappe._("Prerequisite {0} → {1} is duplicated.").format(*edge))
			edges.add(edge)
			graph[row.course].add(row.prerequisite_course)

		visiting, visited = set(), set()

		def visit(course):
			if course in visiting:
				return True
			if course in visited:
				return False
			visiting.add(course)
			if any(visit(required) for required in graph[course]):
				return True
			visiting.remove(course)
			visited.add(course)
			return False

		if any(visit(course) for course in graph):
			frappe.throw(frappe._("Curriculum prerequisites cannot contain a cycle."))

	def _validate_immutable_structure(self, previous):
		fields = ("version_label", "programme", "effective_from_session", "effective_to_session", "notes")
		if any(self.get(field) != previous.get(field) for field in fields):
			frappe.throw(frappe._("An Active or Retired curriculum cannot be structurally changed."))

		course_fields = ("course", "academic_level", "semester_number", "course_category", "credit_units")
		prerequisite_fields = ("course", "prerequisite_course")
		if self._rows(self.courses, course_fields) != self._rows(
			previous.courses, course_fields
		) or self._rows(self.prerequisites, prerequisite_fields) != self._rows(
			previous.prerequisites, prerequisite_fields
		):
			frappe.throw(frappe._("An Active or Retired curriculum cannot be structurally changed."))

	@staticmethod
	def _rows(rows, fields):
		return [tuple(row.get(field) for field in fields) for row in rows]
