import frappe
from frappe.tests import IntegrationTestCase


class TestFoundationModel(IntegrationTestCase):
	def setUp(self):
		self.institution = (
			frappe.db.get_value("Institution", {}, "name")
			or self._insert(
				"Institution",
				institution_code="test-inst",
				institution_name="Test Institution",
				institution_type="College",
			).name
		)

	def test_codes_are_normalised_and_immutable(self):
		campus = self._insert(
			"Campus",
			campus_code="main-campus",
			campus_name="Main Campus",
			institution=self.institution,
		)
		self.assertEqual(campus.name, "MAIN-CAMPUS")

		campus.campus_code = "OTHER"
		with self.assertRaises(frappe.ValidationError):
			campus.save()

		with self.assertRaises(frappe.ValidationError):
			self._insert(
				"Institution",
				institution_code="another",
				institution_name="Another Institution",
				institution_type="College",
			)

	def test_semester_must_fit_its_session(self):
		session = self._insert(
			"Academic Session",
			session_code="test-2026",
			session_name="Test 2026",
			start_date="2026-01-01",
			end_date="2026-12-31",
		)
		with self.assertRaises(frappe.ValidationError):
			self._insert(
				"Academic Semester",
				academic_session=session.name,
				semester_name="First Semester",
				semester_number=1,
				start_date="2025-12-01",
				end_date="2026-05-31",
			)

	def test_curriculum_integrity_and_lifecycle(self):
		faculty = self._insert(
			"Faculty",
			faculty_code="test-sci",
			faculty_name="Test Science",
			institution=self.institution,
		)
		department = self._insert(
			"Department",
			department_code="test-csc",
			department_name="Test Computer Science",
			faculty=faculty.name,
		)
		programme = self._insert(
			"Programme",
			programme_code="test-bsc-csc",
			programme_name="Test BSc Computer Science",
			department=department.name,
			award_title="BSc Computer Science",
			duration_years=4,
			duration_semesters=8,
			minimum_credit_load=12,
			maximum_credit_load=24,
		)
		level = self._insert(
			"Academic Level", level_code="test-100", level_name="Test 100 Level", sequence=91
		)
		category = self._insert("Course Category", category_code="test-core", category_name="Test Core")
		course_a = self._insert(
			"Course",
			course_code="test-csc101",
			course_title="Test Introduction",
			owning_department=department.name,
			default_category=category.name,
			default_credit_units=3,
		)
		course_b = self._insert(
			"Course",
			course_code="test-csc201",
			course_title="Test Intermediate",
			owning_department=department.name,
			default_category=category.name,
			default_credit_units=3,
		)
		session = self._insert(
			"Academic Session",
			session_code="test-2027",
			session_name="Test 2027",
			start_date="2027-01-01",
			end_date="2027-12-31",
		)

		curriculum = frappe.get_doc(
			{
				"doctype": "Curriculum Version",
				"curriculum_code": "test-csc-v1",
				"version_label": "Test Version 1",
				"programme": programme.name,
				"effective_from_session": session.name,
				"courses": [
					self._curriculum_course(course_a.name, level.name, category.name, 1),
					self._curriculum_course(course_b.name, level.name, category.name, 3),
				],
				"prerequisites": [
					{"course": course_a.name, "prerequisite_course": course_b.name},
					{"course": course_b.name, "prerequisite_course": course_a.name},
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			curriculum.insert()

		curriculum.prerequisites = []
		curriculum.append("prerequisites", {"course": course_b.name, "prerequisite_course": course_a.name})
		curriculum.insert()
		curriculum.status = "Under Review"
		curriculum.save()
		curriculum.status = "Active"
		curriculum.save()

		curriculum.notes = "This edit must be rejected"
		with self.assertRaises(frappe.ValidationError):
			curriculum.save()

	@staticmethod
	def _curriculum_course(course, level, category, semester):
		return {
			"course": course,
			"academic_level": level,
			"semester_number": semester,
			"course_category": category,
			"credit_units": 3,
		}

	@staticmethod
	def _insert(doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert()
