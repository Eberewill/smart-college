frappe.ready(() => {
	document.addEventListener("click", async (event) => {
		const button = event.target.closest("[data-action]");
		if (!button || button.disabled) return;
		event.preventDefault();
		button.disabled = true;
		try {
			await run_action(button);
		} catch (error) {
			frappe.msgprint(error.message || __("The action could not be completed."));
			button.disabled = false;
		}
	});
});

async function call(method, args) {
	const response = await frappe.call({ method, args, type: "POST", freeze: true });
	return response.message;
}

async function run_action(button) {
	const action = button.dataset.action;
	if (action === "create") {
		await call("college_management.academics.create_course_registration", {
			enrolment: button.dataset.enrolment,
			academic_semester: button.dataset.semester,
		});
	} else if (action === "save" || action === "submit") {
		const registration = button.dataset.registration;
		const form = document.querySelector(
			`[data-registration-form="${CSS.escape(registration)}"]`
		);
		const courses = [...form.querySelectorAll('input[type="checkbox"]:checked')].map(
			(field) => field.value
		);
		await call("college_management.academics.save_course_registration", {
			registration,
			courses,
		});
		if (action === "submit")
			await call("college_management.academics.submit_course_registration", {
				registration,
			});
	} else if (action === "reopen") {
		const reason = window.prompt(__("Why do you need to add or drop a course?"));
		if (!reason) {
			button.disabled = false;
			return;
		}
		await call("college_management.academics.reopen_course_registration", {
			registration: button.dataset.registration,
			reason,
		});
	}
	window.location.reload();
}
