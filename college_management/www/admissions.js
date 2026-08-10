document.addEventListener("click", async (event) => {
	const button = event.target.closest('[data-action="create"]');
	if (!button || button.disabled) return;
	button.disabled = true;
	try {
		const response = await frappe.call({
			method: "college_management.college_management_system.doctype.admission_application.admission_application.create_application",
			args: { admission_programme: button.dataset.offering },
			type: "POST",
			freeze: true,
		});
		window.location.assign(`/admissions/${encodeURIComponent(response.message.application)}`);
	} catch (error) {
		frappe.msgprint(error.message || __("The application could not be started."));
		button.disabled = false;
	}
});
