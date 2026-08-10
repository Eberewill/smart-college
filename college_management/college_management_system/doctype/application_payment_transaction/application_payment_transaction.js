frappe.ui.form.on("Application Payment Transaction", {
	refresh(frm) {
		if (!frm.is_new() && can_reconcile()) {
			frm.add_custom_button(__("Reconcile with gateway"), async () => {
				await frappe.call({
					method: "college_management.payments.reconcile_payment",
					type: "POST",
					args: { reference: frm.doc.payment_reference },
					freeze: true,
				});
				frm.reload_doc();
			});
		}
	},
});

function can_reconcile() {
	return ["System Manager", "Institution Super Admin", "Finance Officer"].some((role) =>
		frappe.user.has_role(role)
	);
}
