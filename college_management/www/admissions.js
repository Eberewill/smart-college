frappe.ready(() => {
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
