import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, nowdate

from college_management.academics import (
	approve_course_registration,
	change_student_status,
	create_course_registration,
	enrol_student,
	lock_course_registration,
	record_prior_course,
	reopen_course_registration,
	review_course_registration,
	save_course_registration,
	submit_course_registration,
)
from college_management.college_management_system.doctype.admission_application.admission_application import (
	create_application,
	submit_application,
)
from college_management.www.student import get_context


class TestStudentAcademics(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=6).upper()
		institution = frappe.db.get_value("Institution", {}, "name")
		self.institution = frappe.get_doc("Institution", institution)
		self.session = self._insert(
			"Academic Session",
			session_code=f"AC-{self.suffix}",
			session_name=f"Academic {self.suffix}",
			start_date=add_days(nowdate(), -30),
			end_date=add_days(nowdate(), 300),
			status="Open",
		)
		self.semester = self._insert(
			"Academic Semester",
			academic_session=self.session.name,
			semester_name="First Semester",
			semester_number=1,
			start_date=add_days(nowdate(), -1),
			end_date=add_days(nowdate(), 120),
			registration_start_date=add_days(nowdate(), -10),
			registration_end_date=add_days(nowdate(), 5),
			add_drop_deadline=add_days(nowdate(), 10),
			status="Open",
		)
		faculty = self._insert(
			"Faculty",
			faculty_code=f"AF-{self.suffix}",
			faculty_name=f"Academic Faculty {self.suffix}",
			institution=self.institution.name,
		)
		self.department = self._insert(
			"Department",
			department_code=f"AD-{self.suffix}",
			department_name=f"Academic Department {self.suffix}",
			faculty=faculty.name,
		)
		self.programme = self._insert(
			"Programme",
			programme_code=f"AP-{self.suffix}",
			programme_name=f"Academic Programme {self.suffix}",
			department=self.department.name,
			award_title="Diploma",
			duration_years=2,
			duration_semesters=4,
			minimum_credit_load=3,
			maximum_credit_load=6,
		)
		self.level = self._insert(
			"Academic Level",
			level_code=f"AL-{self.suffix}",
			level_name=f"Level {self.suffix}",
			sequence=frappe.db.count("Academic Level") + 100,
		)
		category = self._insert(
			"Course Category",
			category_code=f"CORE-{self.suffix}",
			category_name=f"Core {self.suffix}",
		)
		self.prerequisite = self._insert(
			"Course",
			course_code=f"PRE-{self.suffix}",
			course_title="Foundation Course",
			owning_department=self.department.name,
			default_category=category.name,
			default_credit_units=3,
		)
		self.course = self._insert(
			"Course",
			course_code=f"ADV-{self.suffix}",
			course_title="Advanced Course",
			owning_department=self.department.name,
			default_category=category.name,
			default_credit_units=3,
		)
		self.curriculum = self._insert(
			"Curriculum Version",
			curriculum_code=f"CUR-{self.suffix}",
			version_label=f"Curriculum {self.suffix}",
			programme=self.programme.name,
			effective_from_session=self.session.name,
			courses=[
				self._curriculum_course(self.prerequisite.name, category.name),
				self._curriculum_course(self.course.name, category.name),
			],
			prerequisites=[{"course": self.course.name, "prerequisite_course": self.prerequisite.name}],
		)
		self.curriculum.status = "Under Review"
		self.curriculum.save()
		self.curriculum.status = "Active"
		self.curriculum.save()
		self.student_user, self.student = self._student()

	def test_governed_enrolment_registration_status_and_history(self):
		registry = self._staff("Registry Officer")
		reviewer = self._staff("Academic Approver")
		approver = self._staff("Academic Approver")

		frappe.set_user(registry.name)
		enrolment = enrol_student(
			self.student.name, self.session.name, self.level.name, self.curriculum.name
		)["enrolment"]
		self.assertEqual(
			enrol_student(self.student.name, self.session.name, self.level.name)["enrolment"], enrolment
		)

		frappe.set_user(self.student_user.name)
		registration = create_course_registration(enrolment, self.semester.name)["registration"]
		save_course_registration(registration, [self.course.name])
		with self.assertRaises(frappe.ValidationError):
			submit_course_registration(registration)

		frappe.set_user(registry.name)
		record_prior_course(
			self.student.name,
			self.prerequisite.name,
			"Passed",
			nowdate(),
			"Verified transfer transcript",
		)
		frappe.set_user(self.student_user.name)
		self.assertEqual(submit_course_registration(registration)["status"], "Submitted")

		frappe.set_user(reviewer.name)
		self.assertEqual(
			review_course_registration(registration, "Credit load checked")["status"], "Reviewed"
		)
		with self.assertRaises(frappe.PermissionError):
			approve_course_registration(registration)
		frappe.set_user(approver.name)
		self.assertEqual(approve_course_registration(registration)["status"], "Approved")

		frappe.set_user(self.student_user.name)
		self.assertEqual(reopen_course_registration(registration, "Add foundation course")["status"], "Draft")
		save_course_registration(registration, [self.prerequisite.name, self.course.name])
		submit_course_registration(registration)
		frappe.set_user(reviewer.name)
		review_course_registration(registration)
		frappe.set_user(approver.name)
		approve_course_registration(registration)
		frappe.set_user(registry.name)
		self.assertEqual(lock_course_registration(registration)["status"], "Locked")
		locked = frappe.get_doc("Course Registration", registration)
		locked.flags.academic_action = True
		with self.assertRaises(frappe.ValidationError):
			locked.save(ignore_permissions=True)

		self.assertEqual(
			change_student_status(self.student.name, "Deferred", nowdate(), "Approved leave")["status"],
			"Deferred",
		)
		with self.assertRaises(frappe.ValidationError):
			change_student_status(self.student.name, "Graduated", nowdate(), "Invalid transition")
		self.assertEqual(
			change_student_status(self.student.name, "Active", nowdate(), "Returned")["status"], "Active"
		)

		frappe.set_user(self.student_user.name)
		context = frappe._dict()
		get_context(context)
		self.assertEqual(context.profile.name, self.student.name)
		self.assertEqual(context.registrations[0].status, "Locked")
		self.assertTrue(frappe.get_doc("Course Registration", registration).has_permission("print"))
		self.assertFalse(frappe.get_doc("Course Registration", registration).has_permission("write"))
		self.assertGreaterEqual(len(context.history), 6)
		frappe.set_user("Administrator")

	def _student(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"student-{frappe.generate_hash(length=8)}@example.test",
				"first_name": "Test",
				"last_name": "Student",
				"enabled": 1,
				"user_type": "Website User",
				"send_welcome_email": 0,
				"roles": [{"role": "Applicant"}, {"role": "Student"}],
			}
		).insert(ignore_permissions=True)
		profile = frappe.get_doc("Applicant Profile", {"user": user.name})
		cycle = self._insert(
			"Admission Cycle",
			admission_cycle_code=f"ACYCLE-{self.suffix}",
			cycle_name=f"Academic Cycle {self.suffix}",
			academic_session=self.session.name,
			applications_open_from=add_days(now_datetime(), -1),
			applications_close_at=add_days(now_datetime(), 30),
			decision_deadline=add_days(nowdate(), 60),
		)
		offering = self._insert(
			"Admission Programme",
			admission_cycle=cycle.name,
			programme=self.programme.name,
			application_fee=0,
			currency="NGN",
		)
		cycle.status = "Under Review"
		cycle.save()
		cycle.status = "Published"
		cycle.save()
		frappe.set_user(user.name)
		application = create_application(offering.name)["application"]
		submit_application(application)
		frappe.set_user("Administrator")
		student = frappe.get_doc(
			{
				"doctype": "Student Profile",
				"user": user.name,
				"applicant_profile": profile.name,
				"admission_application": application,
				"programme": self.programme.name,
				"department": self.department.name,
				"admission_cycle": cycle.name,
				"academic_session": self.session.name,
				"admission_date": nowdate(),
				"first_name": "Test",
				"last_name": "Student",
			}
		)
		student.owner = user.name
		student.insert(ignore_permissions=True)
		return user, student

	def _curriculum_course(self, course, category):
		return {
			"course": course,
			"academic_level": self.level.name,
			"semester_number": 1,
			"course_category": category,
			"credit_units": 3,
		}

	@staticmethod
	def _staff(role):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": f"academic-{frappe.generate_hash(length=8)}@example.test",
				"first_name": "Academic",
				"last_name": "Staff",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def _insert(doctype, **values):
		return frappe.get_doc({"doctype": doctype, **values}).insert()
