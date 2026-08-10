frappe.ui.form.on("Student Profile", {
	refresh(frm) {
		if (frm.is_new() || !can_manage_students()) return;
		frm.add_custom_button(__("Enrol for session"), () => enrol_student(frm), __("Academics"));
		frm.add_custom_button(__("Change status"), () => change_status(frm), __("Academics"));
		frm.add_custom_button(
			__("Record prior course"),
			() => record_prior_course(frm),
			__("Academics")
		);
	},
});

function can_manage_students() {
	return ["System Manager", "Institution Super Admin", "Registry Officer"].some((role) =>
		frappe.user.has_role(role)
	);
}

function enrol_student(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Enrol student"),
		fields: [
			{
				fieldname: "academic_session",
				fieldtype: "Link",
				label: __("Academic Session"),
				options: "Academic Session",
				reqd: 1,
			},
			{
				fieldname: "academic_level",
				fieldtype: "Link",
				label: __("Academic Level"),
				options: "Academic Level",
				reqd: 1,
			},
			{
				fieldname: "curriculum_version",
				fieldtype: "Link",
				label: __("Curriculum Version"),
				options: "Curriculum Version",
			},
		],
		primary_action_label: __("Enrol"),
		async primary_action(values) {
			const response = await frappe.call({
				method: "college_management.academics.enrol_student",
				type: "POST",
				args: { student: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frappe.set_route("Form", "Student Enrolment", response.message.enrolment);
		},
	});
	dialog.show();
}

function change_status(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Change student status"),
		fields: [
			{
				fieldname: "status",
				fieldtype: "Select",
				label: __("New status"),
				options: [
					"Active",
					"Deferred",
					"Suspended",
					"Withdrawn",
					"Graduated",
					"Archived",
				].filter((status) => status !== frm.doc.status),
				reqd: 1,
			},
			{
				fieldname: "effective_date",
				fieldtype: "Date",
				label: __("Effective date"),
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
		],
		primary_action_label: __("Record change"),
		async primary_action(values) {
			await frappe.call({
				method: "college_management.academics.change_student_status",
				type: "POST",
				args: { student: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
}

function record_prior_course(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Record prior course credit"),
		fields: [
			{
				fieldname: "course",
				fieldtype: "Link",
				label: __("Course"),
				options: "Course",
				reqd: 1,
			},
			{
				fieldname: "outcome",
				fieldtype: "Select",
				label: __("Outcome"),
				options: ["Passed", "Exempted"],
				reqd: 1,
			},
			{
				fieldname: "academic_session",
				fieldtype: "Link",
				label: __("Academic Session"),
				options: "Academic Session",
			},
			{
				fieldname: "effective_date",
				fieldtype: "Date",
				label: __("Effective date"),
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Evidence or reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Record credit"),
		async primary_action(values) {
			await frappe.call({
				method: "college_management.academics.record_prior_course",
				type: "POST",
				args: { student: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frappe.show_alert({ message: __("Prior course credit recorded"), indicator: "green" });
		},
	});
	dialog.show();
}
