frappe.ready(() => {
	const newApplicationButton = document.querySelector("[data-new-application]");
	const newApplicationDialog = document.querySelector("[data-new-application-dialog]");
	const newApplicationForm = document.querySelector("[data-new-application-form]");
	newApplicationButton?.addEventListener("click", () => newApplicationDialog.showModal());
	document.querySelector("[data-new-application-cancel]")?.addEventListener("click", () => newApplicationDialog.close());
	newApplicationForm?.addEventListener("submit", async (event) => {
		event.preventDefault();
		const button = newApplicationForm.querySelector('[type="submit"]');
		button.disabled = true;
		try {
			const response = await frappe.call({
				method: "college_management.college_management_system.doctype.admission_application.admission_application.create_application",
				args: { admission_programme: new FormData(newApplicationForm).get("admission_programme") },
				type: "POST",
				freeze: true,
			});
			window.location.assign(`/applications/${encodeURIComponent(response.message.application)}`);
		} catch (error) {
			window.cmPortalNotify?.show({ state: "error", title: __("Application not started"), message: error.message || __("Please try again.") });
			button.disabled = false;
		}
	});

	const search = document.querySelector("[data-application-search]");
	const status = document.querySelector("[data-application-status]");
	const cards = [...document.querySelectorAll("[data-application-card]")];
	const count = document.querySelector("[data-application-count]");
	const empty = document.querySelector("[data-filter-empty]");
	if (!search || !status || !count || !empty) return;

	const filterApplications = () => {
		const query = search.value.trim().toLowerCase();
		const selectedStatus = status.value;
		let visible = 0;
		cards.forEach((card) => {
			const matches =
				(!query || card.dataset.search.includes(query)) &&
				(!selectedStatus || card.dataset.status === selectedStatus);
			card.hidden = !matches;
			visible += matches;
		});
		count.textContent = `${visible} ${visible === 1 ? __("application") : __("applications")}`;
		empty.hidden = visible !== 0;
	};

	search.addEventListener("input", filterApplications);
	status.addEventListener("change", filterApplications);
});
