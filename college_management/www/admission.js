const autosaveTimers = new WeakMap();
const saveQueues = new WeakMap();
const frappeControls = new Map();

document.addEventListener("input", (event) => {
	const form = event.target.closest("[data-application-form]");
	if (form && event.target.type !== "file" && !event.target.matches("[data-control-value]")) {
		schedule_save(form);
	}
});
document.addEventListener("change", (event) => {
	const form = event.target.closest("[data-application-form]");
	if (form && !event.target.matches("[data-control-value]")) {
		schedule_save(form, event.target.type === "file" ? 0 : 800);
	}
});
document.addEventListener("click", handle_click);

frappe.ready(() => {
	document
		.querySelectorAll("[data-step-next], [data-step-back], [data-step-target]")
		.forEach((button) => button.addEventListener("click", handle_navigation));
	frappe.require("controls.bundle.js", setup_frappe_controls);
});

function setup_frappe_controls() {
	document.querySelectorAll("[data-frappe-control]").forEach((wrapper) => {
		const hidden = wrapper.querySelector("[data-control-value]");
		const form = wrapper.closest("[data-application-form]");
		const control = frappe.ui.form.make_control({
			parent: $(wrapper),
			render_input: true,
			df: {
				fieldname: wrapper.dataset.controlName,
				fieldtype: wrapper.dataset.fieldtype,
				label: wrapper.dataset.label,
				options: wrapper.dataset.options || undefined,
				reqd: Number(wrapper.dataset.required),
				change: () => {
					hidden.value = control.get_value() || "";
					schedule_save(form);
				},
			},
		});
		control.set_input(hidden.value);
		frappeControls.set(wrapper, control);
	});
}

async function handle_click(event) {
	const navigation = event.target.closest("[data-step-next], [data-step-back], [data-step-target]");
	if (navigation) {
		event.preventDefault();
		await navigate(navigation);
		return;
	}
	const button = event.target.closest("[data-action]");
	if (!button || button.disabled) return;
	event.preventDefault();
	show_portal_error("");
	button.disabled = true;
	try {
		await run_action(button);
	} catch (error) {
		show_portal_error(error.message || __("The action could not be completed."));
		button.disabled = false;
	}
}

async function handle_navigation(event) {
	event.stopPropagation();
	event.preventDefault();
	await navigate(event.currentTarget);
}

async function navigate(button) {
	const form = button.closest("form");
	const current = Number(form.querySelector(".cm-wizard-step:not([hidden])").dataset.step);
	const target = button.hasAttribute("data-step-next")
		? current + 1
		: button.hasAttribute("data-step-back")
			? current - 1
			: Number(button.dataset.stepTarget);
	if (target > current && !step_is_valid(form, current)) return;
	show_portal_error("");
	button.disabled = true;
	try {
		await persist_application(form);
		show_step(form, target);
	} catch (error) {
		show_portal_error(error.message || __("Your changes could not be saved."));
	} finally {
		button.disabled = false;
	}
}

async function call(method, args) {
	const response = await frappe.call({ method, args, type: "POST", freeze: true });
	return response.message;
}

async function run_action(button) {
	const action = button.dataset.action;
	if (action === "submit") {
		const form = [...document.querySelectorAll("[data-application-form]")].find(
			(candidate) => candidate.dataset.applicationForm === button.dataset.application
		);
		if (!form_is_valid(form)) throw new Error(__("Complete the required fields first."));
		await persist_application(form);
		await call(
			"college_management.college_management_system.doctype.admission_application.admission_application.submit_application",
			{ application: button.dataset.application }
		);
	} else if (action === "save-exit") {
		const form = button.closest("[data-application-form]");
		await persist_application(form);
		window.location.assign("/admissions");
		return;
	} else if (action === "invoice") {
		await call("college_management.payments.create_application_invoice", { application: button.dataset.application });
	} else if (action === "pay") {
		const payment = await call("college_management.payments.initialize_payment", { invoice: button.dataset.invoice });
		window.location.assign(payment.authorization_url);
		return;
	} else if (action === "verify") {
		await call("college_management.payments.verify_payment", { reference: button.dataset.reference });
	} else if (action === "respond") {
		if (!window.confirm(__("Confirm that you want to {0} this offer?", [button.dataset.response.toLowerCase()]))) {
			button.disabled = false;
			return;
		}
		await call("college_management.admissions.respond_to_admission", { letter: button.dataset.letter, response: button.dataset.response });
	}
	window.location.reload();
}

function schedule_save(form, delay = 800) {
	clearTimeout(autosaveTimers.get(form));
	set_save_status(form, __("Saving…"));
	autosaveTimers.set(
		form,
		setTimeout(
			() =>
				persist_application(form).catch((error) => {
					set_save_status(form, __("Changes not saved"), true);
					show_portal_error(error.message || __("Your changes could not be saved."));
				}),
			delay
		)
	);
}

function persist_application(form) {
	const save = (saveQueues.get(form) || Promise.resolve()).catch(() => {}).then(() => save_application_now(form));
	saveQueues.set(form, save);
	return save;
}

async function save_application_now(form) {
	clearTimeout(autosaveTimers.get(form));
	set_save_status(form, __("Saving…"));
	const profile = {};
	for (const field of form.querySelectorAll("[data-profile-key]")) profile[field.dataset.profileKey] = field.value;
	await call("college_management.www.admissions.save_applicant_profile", { values: profile });
	const responses = [];
	for (const field of form.querySelectorAll("[data-key]")) {
		const response = { field_key: field.dataset.key };
		if (field.dataset.type === "Attachment") {
			if (field.files.length) {
				response.attachment = await upload_file(field.files[0], form.dataset.applicationForm);
				field.dataset.current = response.attachment;
				field.value = "";
				field.required = false;
			} else response.attachment = field.dataset.current || "";
		} else response.response_value = field.dataset.type === "Check" ? (field.checked ? "1" : "0") : field.value;
		responses.push(response);
	}
	await call(
		"college_management.college_management_system.doctype.admission_application.admission_application.save_application_responses",
		{ application: form.dataset.applicationForm, responses }
	);
	set_save_status(form, __("All changes saved"));
	show_portal_error("");
}

function step_is_valid(form, index) {
	const step = [...form.querySelectorAll("[data-step]")].find(
		(candidate) => Number(candidate.dataset.step) === index
	);
	for (const wrapper of step.querySelectorAll("[data-frappe-control][data-required='1']")) {
		const value = frappeControls.get(wrapper)?.get_value() || wrapper.querySelector("[data-control-value]").value;
		if (!value) {
			show_portal_error(__("{0} is required.", [wrapper.dataset.label]));
			return false;
		}
	}
	for (const field of step.querySelectorAll("input:not([type='hidden']), select, textarea")) {
		if (!field.checkValidity()) {
			field.reportValidity();
			return false;
		}
	}
	return true;
}

function form_is_valid(form) {
	for (const step of form.querySelectorAll("[data-step]")) {
		if (!step_is_valid(form, Number(step.dataset.step))) {
			show_step(form, Number(step.dataset.step));
			return false;
		}
	}
	return true;
}

function show_step(form, index) {
	const steps = [...form.querySelectorAll("[data-step]")];
	if (!steps[index]) return;
	steps.forEach((step, position) => (step.hidden = position !== index));
	form.querySelectorAll("[data-step-target]").forEach((button, position) => {
		button.setAttribute("aria-current", position === index ? "step" : "false");
		const state = button.querySelector("[data-step-state]");
		if (state) {
			const complete = position < index;
			button.dataset.stepState = complete ? "complete" : position === index ? "current" : "upcoming";
			state.dataset.stepState = button.dataset.stepState;
			state.textContent = complete ? __("Completed") : position === index ? __("In progress") : __("Not started");
		}
	});
	const progress = form.querySelector("[data-step-progress]");
	if (progress) progress.textContent = __("Step {0} of {1}", [index + 1, steps.length]);
	const progressBar = form.querySelector("[data-step-progress-bar]");
	if (progressBar) progressBar.style.width = `${((index + 1) / steps.length) * 100}%`;
	const progressPercent = form.querySelector("[data-progress-percent]");
	if (progressPercent) progressPercent.textContent = `${Math.round(((index + 1) / steps.length) * 100)}% ${__("complete")}`;
	update_review(form);
	steps[index].querySelector("h2")?.focus({ preventScroll: true });
}

function update_review(form) {
	for (const output of form.querySelectorAll("[data-review-profile]")) {
		const input = [...form.querySelectorAll("[data-profile-key]")].find(
			(candidate) => candidate.dataset.profileKey === output.dataset.reviewProfile
		);
		output.textContent = input?.value || __("Not provided");
	}
	for (const output of form.querySelectorAll("[data-review-field]")) {
		const input = [...form.querySelectorAll("[data-key]")].find(
			(candidate) => candidate.dataset.key === output.dataset.reviewField
		);
		let value = input?.value;
		if (output.dataset.reviewType === "Check") value = input?.checked ? __("Yes") : __("No");
		if (output.dataset.reviewType === "Attachment") value = input?.files[0]?.name || input?.dataset.current;
		output.textContent = value || __("Not provided");
	}
}

function set_save_status(form, message, error = false) {
	form.querySelectorAll("[data-save-status]").forEach((status) => {
		status.textContent = message;
		status.classList.toggle("text-danger", error);
	});
}

function show_portal_error(message) {
	const alert = document.querySelector("[data-portal-error]");
	if (!alert) return;
	alert.textContent = message;
	alert.classList.toggle("d-none", !message);
}

async function upload_file(file, application) {
	const body = new FormData();
	body.append("file", file);
	body.append("is_private", "1");
	body.append("doctype", "Admission Application");
	body.append("docname", application);
	const response = await fetch("/api/method/upload_file", { method: "POST", headers: { "X-Frappe-CSRF-Token": frappe.csrf_token }, body });
	const result = await response.json();
	if (!response.ok || result.exc) throw new Error(result.message || __("File upload failed."));
	return result.message.file_url;
}
