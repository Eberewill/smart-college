frappe.ui.form.on("Admission Review", {
	refresh(frm) {
		if (
			!frm.is_new() &&
			frm.doc.status === "Assigned" &&
			frm.doc.assigned_to === frappe.session.user
		) {
			frm.add_custom_button(__("Complete review"), () => complete_review(frm));
		}
	},
});

function complete_review(frm) {
	const fields = [];
	frm.doc.checks.forEach((check, index) => {
		fields.push(
			{
				fieldname: `check_${index}_result`,
				fieldtype: "Select",
				label: check.check_label,
				options: ["Pass", "Fail", "Not Applicable"],
				reqd: 1,
			},
			{
				fieldname: `check_${index}_notes`,
				fieldtype: "Small Text",
				label: __("Notes for {0}", [check.check_label]),
			}
		);
	});
	fields.push(
		{
			fieldname: "score",
			fieldtype: "Float",
			label: __("Score out of {0}", [frm.doc.max_score]),
			reqd: 1,
		},
		{
			fieldname: "recommendation",
			fieldtype: "Select",
			label: __("Recommendation"),
			options: ["Recommend Admission", "Recommend Rejection", "Refer"],
			reqd: 1,
		},
		{ fieldname: "comments", fieldtype: "Small Text", label: __("Reviewer comments") }
	);
	const dialog = new frappe.ui.Dialog({
		title: __("Complete {0}", [frm.doc.stage_name]),
		fields,
		primary_action_label: __("Submit review"),
		async primary_action(values) {
			const checks = {};
			frm.doc.checks.forEach((check, index) => {
				checks[check.check_label] = {
					result: values[`check_${index}_result`],
					notes: values[`check_${index}_notes`],
				};
			});
			await frappe.call({
				method: "college_management.admissions.complete_review",
				type: "POST",
				args: {
					review: frm.doc.name,
					checks,
					score: values.score,
					recommendation: values.recommendation,
					comments: values.comments,
				},
				freeze: true,
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
}
