(() => {
    const modal = document.getElementById("conversationProfileModal");
    if (!modal) return;

    const closeButton = modal.querySelector(".conversation-profile-close");
    const userName = (modal.dataset.profileUser || "").trim();
    let lastFocused = null;

    const findOpeners = () => {
        const explicit = [...document.querySelectorAll("[data-profile-open]")];
        const userChips = [...document.querySelectorAll(".user-chip")];
        const candidates = [...document.querySelectorAll(".header-actions span, .header-actions button, .header-actions a")];
        const byText = userName
            ? candidates.filter((el) => el.textContent.trim() === userName)
            : [];

        return [...new Set([...explicit, ...userChips, ...byText])];
    };

    const openModal = () => {
        lastFocused = document.activeElement;
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("profile-modal-open");
        window.requestAnimationFrame(() => closeButton?.focus());
    };

    const closeModal = () => {
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("profile-modal-open");
        if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
    };

    findOpeners().forEach((opener) => {
        opener.classList.add("profile-trigger");
        opener.setAttribute("role", opener.tagName === "BUTTON" ? "button" : "button");
        if (!opener.hasAttribute("tabindex") && opener.tagName !== "BUTTON" && opener.tagName !== "A") {
            opener.setAttribute("tabindex", "0");
        }
        opener.setAttribute("aria-haspopup", "dialog");
        opener.setAttribute("aria-controls", "conversationProfileModal");
        opener.addEventListener("click", (event) => {
            // If this is a plain user-name link/button, prefer the profile modal.
            if (opener.classList.contains("user-chip") || opener.textContent.trim() === userName) {
                event.preventDefault();
            }
            openModal();
        });
        opener.addEventListener("keydown", (event) => {
            if ((event.key === "Enter" || event.key === " ") && opener.tagName !== "BUTTON") {
                event.preventDefault();
                openModal();
            }
        });
    });

    modal.querySelectorAll("[data-profile-close]").forEach((closer) => {
        closer.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) closeModal();
    });
})();
