frappe.ui.form.on("Admission Decision", {
	async refresh(frm) {
		if (frm.is_new() || frm.doc.outcome !== "Admitted" || !can_issue_letter()) return;
		const existing = await frappe.db.get_list("Admission Letter", {
			filters: { admission_decision: frm.doc.name },
			fields: ["name"],
			limit: 1,
		});
		if (!existing.length)
			frm.add_custom_button(__("Issue admission letter"), () => issue_letter(frm));
	},
});

function can_issue_letter() {
	return ["System Manager", "Institution Super Admin", "Admissions Officer"].some((role) =>
		frappe.user.has_role(role)
	);
}

function issue_letter(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Issue admission letter"),
		fields: [
			{
				fieldname: "acceptance_deadline",
				fieldtype: "Date",
				label: __("Acceptance deadline"),
				reqd: 1,
			},
		],
		primary_action_label: __("Issue letter"),
		async primary_action(values) {
			const response = await frappe.call({
				method: "college_management.admissions.issue_admission_letter",
				type: "POST",
				args: { decision: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frappe.set_route("Form", "Admission Letter", response.message.letter);
		},
	});
	dialog.show();
}
