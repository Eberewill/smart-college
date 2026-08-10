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
		await call(
			"college_management.college_management_system.doctype.admission_application.admission_application.create_application",
			{ admission_programme: button.dataset.offering }
		);
	} else if (action === "save" || action === "submit") {
		await save_application(button.dataset.application);
		if (action === "submit") {
			await call(
				"college_management.college_management_system.doctype.admission_application.admission_application.submit_application",
				{ application: button.dataset.application }
			);
		}
	} else if (action === "invoice") {
		await call("college_management.payments.create_application_invoice", {
			application: button.dataset.application,
		});
	} else if (action === "pay") {
		const payment = await call("college_management.payments.initialize_payment", {
			invoice: button.dataset.invoice,
		});
		window.location.assign(payment.authorization_url);
		return;
	} else if (action === "verify") {
		await call("college_management.payments.verify_payment", {
			reference: button.dataset.reference,
		});
	} else if (action === "respond") {
		if (
			!window.confirm(
				__("Confirm that you want to {0} this offer?", [
					button.dataset.response.toLowerCase(),
				])
			)
		) {
			button.disabled = false;
			return;
		}
		await call("college_management.admissions.respond_to_admission", {
			letter: button.dataset.letter,
			response: button.dataset.response,
		});
	}
	window.location.reload();
}

async function save_application(application) {
	const form = document.querySelector(`[data-application-form="${CSS.escape(application)}"]`);
	if (!form.reportValidity()) throw new Error(__("Complete the required fields first."));
	const responses = [];
	for (const field of form.querySelectorAll("[data-key]")) {
		const response = { field_key: field.dataset.key };
		if (field.dataset.type === "Attachment") {
			response.attachment = field.files.length
				? await upload_file(field.files[0], application)
				: field.dataset.current || "";
		} else {
			response.response_value =
				field.dataset.type === "Check" ? (field.checked ? "1" : "0") : field.value;
		}
		responses.push(response);
	}
	await call(
		"college_management.college_management_system.doctype.admission_application.admission_application.save_application_responses",
		{ application, responses }
	);
}

async function upload_file(file, application) {
	const body = new FormData();
	body.append("file", file);
	body.append("is_private", "1");
	body.append("doctype", "Admission Application");
	body.append("docname", application);
	const response = await fetch("/api/method/upload_file", {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		body,
	});
	const result = await response.json();
	if (!response.ok || result.exc) throw new Error(result.message || __("File upload failed."));
	return result.message.file_url;
}
