frappe.ui.form.on("Course Registration", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status === "Submitted" && can_review()) {
			frm.add_custom_button(__("Review"), () => review(frm), __("Registration"));
		}
		if (frm.doc.status === "Reviewed" && can_review()) {
			frm.add_custom_button(
				__("Approve"),
				() => run(frm, "approve_course_registration"),
				__("Registration")
			);
		}
		if (frm.doc.status === "Approved" && can_lock()) {
			frm.add_custom_button(
				__("Lock"),
				() => run(frm, "lock_course_registration"),
				__("Registration")
			);
		}
	},
});

function can_review() {
	return ["System Manager", "Institution Super Admin", "Academic Approver"].some((role) =>
		frappe.user.has_role(role)
	);
}

function can_lock() {
	return can_review() || frappe.user.has_role("Registry Officer");
}

function review(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Review course registration"),
		fields: [{ fieldname: "notes", fieldtype: "Small Text", label: __("Review notes") }],
		primary_action_label: __("Mark reviewed"),
		async primary_action(values) {
			await run(frm, "review_course_registration", values);
			dialog.hide();
		},
	});
	dialog.show();
}

async function run(frm, action, values = {}) {
	await frappe.call({
		method: `college_management.academics.${action}`,
		type: "POST",
		args: { registration: frm.doc.name, ...values },
		freeze: true,
	});
	frm.reload_doc();
}
