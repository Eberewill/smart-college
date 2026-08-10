frappe.ui.form.on("Admission Letter", {
	async refresh(frm) {
		if (frm.is_new() || frm.doc.acceptance_status !== "Accepted" || !can_convert_student())
			return;
		const existing = await frappe.db.get_list("Student Profile", {
			filters: { admission_application: frm.doc.admission_application },
			fields: ["name"],
			limit: 1,
		});
		if (!existing.length) {
			frm.add_custom_button(__("Convert to Student"), async () => {
				const response = await frappe.call({
					method: "college_management.admissions.convert_to_student",
					type: "POST",
					args: { letter: frm.doc.name },
					freeze: true,
				});
				frappe.set_route("Form", "Student Profile", response.message.student);
			});
		}
	},
});

function can_convert_student() {
	return ["System Manager", "Institution Super Admin", "Registry Officer"].some((role) =>
		frappe.user.has_role(role)
	);
}
