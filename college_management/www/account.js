frappe.ready(() => {
	document.querySelector("[data-account-profile]")?.addEventListener("submit", saveProfile);
	document.querySelector("[data-password-form]")?.addEventListener("submit", updatePassword);
	document.addEventListener("click", revokeApp);
});

async function call(method, args) {
	const response = await frappe.call({ method, args, type: "POST", freeze: true });
	return response.message;
}

async function saveProfile(event) {
	event.preventDefault();
	const form = event.currentTarget;
	if (!form.reportValidity()) return;
	const button = form.querySelector("button[type='submit']");
	button.disabled = true;
	try {
		const values = Object.fromEntries(new FormData(form));
		const result = await call("college_management.www.account.save_profile", { values });
		document.querySelector(".cm-account > span:nth-child(2)")?.replaceChildren(result.full_name);
		window.cmPortalNotify.show({ state: "success", title: __("Profile saved"), message: __("Your account details have been updated.") });
	} catch (error) {
		window.cmPortalNotify.show({ state: "error", title: __("Profile not saved"), message: error.message || __("Your profile could not be updated.") });
	} finally {
		button.disabled = false;
	}
}

async function updatePassword(event) {
	event.preventDefault();
	const form = event.currentTarget;
	if (!form.reportValidity()) return;
	const values = Object.fromEntries(new FormData(form));
	if (values.new_password !== values.confirm_password) {
		window.cmPortalNotify.show({ state: "error", title: __("Passwords do not match"), message: __("Enter the same new password in both fields.") });
		return;
	}
	const button = form.querySelector("button[type='submit']");
	button.disabled = true;
	try {
		await call("frappe.core.doctype.user.user.update_password", {
			old_password: values.old_password,
			new_password: values.new_password,
			logout_all_sessions: values.logout_all_sessions ? 1 : 0,
		});
		form.reset();
		window.cmPortalNotify.show({ state: "success", title: __("Password updated"), message: __("Your new password is now active.") });
		setTimeout(() => window.location.assign("/me"), 1200);
	} catch (error) {
		window.cmPortalNotify.show({ state: "error", title: __("Password not updated"), message: error.message || __("Check your current password and try again.") });
		button.disabled = false;
	}
}

async function revokeApp(event) {
	const button = event.target.closest("[data-revoke-app]");
	if (!button || button.disabled) return;
	if (!(await window.cmPortalNotify.confirm({
		state: "warning",
		title: __("Revoke application access?"),
		message: __("{0} will no longer be able to access your account.", [button.dataset.appName]),
		confirmLabel: __("Revoke access"),
	}))) return;
	button.disabled = true;
	try {
		await call("college_management.www.account.revoke_app", { client: button.dataset.revokeApp });
		window.location.reload();
	} catch (error) {
		button.disabled = false;
		window.cmPortalNotify.show({ state: "error", title: __("Access not revoked"), message: error.message || __("Try again.") });
	}
}
