frappe.ready(() => {
	document.addEventListener("click", async (event) => {
		const button = event.target.closest("[data-admission-response]");
		if (!button || button.disabled) return;
		const response = button.dataset.admissionResponse;
		const confirmed = await window.cmPortalNotify.confirm({
			state: response === "Accepted" ? "success" : "warning",
			title: response === "Accepted" ? __("Accept admission offer?") : __("Decline admission offer?"),
			message: __("Confirm that you want to {0} this offer.", [response.toLowerCase()]),
			confirmLabel: response === "Accepted" ? __("Accept offer") : __("Decline offer"),
		});
		if (!confirmed) return;
		button.disabled = true;
		try {
			await frappe.call({
				method: "college_management.admissions.respond_to_admission",
				args: { letter: button.dataset.letter, response },
				type: "POST",
				freeze: true,
			});
			window.location.reload();
		} catch (error) {
			button.disabled = false;
			window.cmPortalNotify.show({
				state: "error",
				title: __("Response unsuccessful"),
				message: error.message || __("Your admission response could not be saved."),
			});
		}
	});
});
