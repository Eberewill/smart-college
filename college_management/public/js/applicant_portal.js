(() => {
	const states = {
		error: { icon: "×", timeout: 7000 },
		success: { icon: "✓", timeout: 4500 },
		warning: { icon: "!", timeout: 6000 },
	};

	function normalizeState(state) {
		return states[state] ? state : "success";
	}

	function show({ state = "success", title = "", message = "" }) {
		const stack = document.querySelector("[data-portal-notifications]");
		if (!stack) return;
		state = normalizeState(state);
		const notification = document.createElement("div");
		notification.className = "cm-notification";
		notification.dataset.state = state;
		notification.setAttribute("role", state === "error" ? "alert" : "status");

		const icon = document.createElement("span");
		icon.className = "cm-notification-icon";
		icon.setAttribute("aria-hidden", "true");
		icon.textContent = states[state].icon;
		const copy = document.createElement("div");
		const heading = document.createElement("strong");
		heading.textContent = title;
		const text = document.createElement("p");
		text.textContent = message;
		copy.append(heading, text);
		notification.append(icon, copy);
		stack.append(notification);
		setTimeout(() => notification.remove(), states[state].timeout);
	}

	function confirm({ state = "warning", title = "", message = "", confirmLabel = "Continue", cancelLabel = "Cancel" }) {
		const dialog = document.querySelector("[data-portal-confirm]");
		if (!dialog || dialog.open) return Promise.resolve(false);
		state = normalizeState(state);
		dialog.dataset.state = state;
		dialog.querySelector("[data-notification-title]").textContent = title;
		dialog.querySelector("[data-notification-message]").textContent = message;
		dialog.querySelector("[data-notification-confirm]").textContent = confirmLabel;
		dialog.querySelector("[data-notification-cancel]").textContent = cancelLabel;
		return new Promise((resolve) => {
			dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
			dialog.showModal();
		});
	}

	window.cmPortalNotify = { confirm, show };
})();
