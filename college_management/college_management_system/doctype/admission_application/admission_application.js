frappe.ui.form.on("Admission Application", {
	async refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Submitted" || !can_manage_admissions()) return;
		const [reviews, decisions] = await Promise.all([
			frappe.db.get_list("Admission Review", {
				filters: { admission_application: frm.doc.name },
				fields: ["stage_code", "status"],
				limit: 100,
			}),
			frappe.db.get_list("Admission Decision", {
				filters: { admission_application: frm.doc.name },
				fields: ["name"],
				limit: 1,
			}),
		]);
		if (!decisions.length) {
			frm.add_custom_button(
				__("Assign review"),
				() => assign_review(frm, reviews),
				__("Admissions")
			);
			frm.add_custom_button(
				__("Record decision"),
				() => record_decision(frm),
				__("Admissions")
			);
		}
	},
});

function can_manage_admissions() {
	return ["System Manager", "Institution Super Admin", "Admissions Officer"].some((role) =>
		frappe.user.has_role(role)
	);
}

async function assign_review(frm, reviews) {
	const offering = await frappe.db.get_doc("Admission Programme", frm.doc.admission_programme);
	const assigned = new Set(reviews.map((review) => review.stage_code));
	const stages = offering.review_stages.filter((stage) => !assigned.has(stage.stage_code));
	if (!stages.length) {
		frappe.msgprint(__("Every configured review stage is already assigned."));
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Assign admission review"),
		fields: [
			{
				fieldname: "stage_code",
				fieldtype: "Select",
				label: __("Review stage"),
				options: stages.map((stage) => ({
					label: stage.stage_name,
					value: stage.stage_code,
				})),
				reqd: 1,
			},
			{
				fieldname: "assigned_to",
				fieldtype: "Link",
				label: __("Reviewer"),
				options: "User",
				reqd: 1,
				get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }),
			},
		],
		primary_action_label: __("Assign"),
		async primary_action(values) {
			await frappe.call({
				method: "college_management.admissions.assign_review",
				type: "POST",
				args: { application: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
}

function record_decision(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Record admission decision"),
		fields: [
			{
				fieldname: "outcome",
				fieldtype: "Select",
				label: __("Outcome"),
				options: ["Admitted", "Rejected"],
				reqd: 1,
			},
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Decision reason"),
				reqd: 1,
			},
			{
				fieldname: "conditions",
				fieldtype: "Small Text",
				label: __("Admission conditions"),
			},
		],
		primary_action_label: __("Record final decision"),
		async primary_action(values) {
			await frappe.call({
				method: "college_management.admissions.record_decision",
				type: "POST",
				args: { application: frm.doc.name, ...values },
				freeze: true,
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
}
