(() => {
    const detectLanguage = (link) => {
        const text = (link.textContent || "").trim().toUpperCase();

        if (text === "PL" || text === "EN") return text;

        try {
            const url = new URL(link.href, window.location.origin);
            const match = url.pathname.match(/\/lang\/(pl|en)\/?$/i);
            return match ? match[1].toUpperCase() : null;
        } catch (_) {
            return null;
        }
    };

    const openProfileModal = () => {
        const modal = document.getElementById("conversationProfileModal");
        if (!modal) return;

        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("profile-modal-open");

        const close = modal.querySelector(".conversation-profile-close");
        window.requestAnimationFrame(() => close?.focus());
    };

    function moveLogoutToProfile(actions) {
        const modal = document.getElementById("conversationProfileModal");
        const content = modal?.querySelector(".conversation-profile-content");
        if (!content) return;

        if (content.querySelector(".profile-logout-form")) return;

        const forms = [...actions.querySelectorAll("form")];
        const logoutForm = forms.find((form) => {
            const action = form.getAttribute("action") || "";
            const text = (form.textContent || "").trim().toLowerCase();
            return /logout/i.test(action) || text.includes("wyloguj") || text.includes("sign out");
        });

        if (!logoutForm) return;

        logoutForm.classList.remove("inline-form");
        logoutForm.classList.add("profile-logout-form");

        const button = logoutForm.querySelector("button");
        if (button) {
            button.classList.remove("link-button");
            button.classList.add("profile-logout-button");
        }

        content.appendChild(logoutForm);
    }

    function buildLanguagePanel(switcher) {
        const allLinks = [...switcher.querySelectorAll("a")];
        const destinations = {};

        allLinks.forEach((link) => {
            const lang = detectLanguage(link);
            if (lang && !destinations[lang]) {
                destinations[lang] = link.href;
            }
        });

        /* Fallback to the Store's stable language endpoints if the previous
           V6/V7 JavaScript left the visual switcher in a broken state. */
        if (!destinations.PL) destinations.PL = "/lang/pl";
        if (!destinations.EN) destinations.EN = "/lang/en";

        let current = (document.documentElement.lang || "pl")
            .toUpperCase()
            .startsWith("EN") ? "EN" : "PL";

        const activeLink = allLinks.find((link) => link.classList.contains("active"));
        if (activeLink) {
            const activeLang = detectLanguage(activeLink);
            if (activeLang) current = activeLang;
        }

        switcher.innerHTML = "";
        switcher.className = "language-switcher account-language-panel";
        switcher.setAttribute("role", "radiogroup");
        switcher.setAttribute("aria-label", "Language");

        ["EN", "PL"].forEach((lang) => {
            const option = document.createElement("a");
            option.href = destinations[lang];
            option.className = "language-account-option";
            option.setAttribute("role", "radio");
            option.setAttribute("aria-checked", lang === current ? "true" : "false");
            option.setAttribute("aria-label", lang === "PL" ? "Polski" : "English");

            if (lang === current) option.classList.add("is-active");

            const radio = document.createElement("span");
            radio.className = "language-account-radio";
            radio.setAttribute("aria-hidden", "true");

            const label = document.createElement("span");
            label.className = "language-account-label";
            label.textContent = lang;

            option.appendChild(radio);
            option.appendChild(label);
            switcher.appendChild(option);
        });
    }

    function init() {
        const header = document.querySelector(".site-header");
        const actions = header?.querySelector(".header-actions");
        const switcher = actions?.querySelector(".language-switcher");

        if (!header || !actions || !switcher) return;

        /* Capture the current user before removing the header-only presentation. */
        const userChip = actions.querySelector(".user-chip");
        const userName = (userChip?.textContent || "").trim();

        /* Normalize language area first. */
        buildLanguagePanel(switcher);

        /* Move logout into the profile modal before hiding/removing it from header. */
        moveLogoutToProfile(actions);

        /* Remove any V6/V7 generated dropdown trigger/menu that may still exist. */
        actions.querySelectorAll(".language-menu-trigger, .language-menu").forEach((el) => el.remove());

        /* Create the Socratic AI-style account + language cluster once. */
        if (!actions.querySelector(".profile-language-cluster")) {
            const cluster = document.createElement("div");
            cluster.className = "profile-language-cluster";

            if (userChip) {
                const profileButton = document.createElement("button");
                profileButton.type = "button";
                profileButton.className = "profile-header-button";
                profileButton.setAttribute("aria-label", userName ? `Profil: ${userName}` : "Profil użytkownika");
                profileButton.setAttribute("aria-haspopup", "dialog");
                profileButton.setAttribute("aria-controls", "conversationProfileModal");

                const image = document.createElement("img");
                image.className = "profile-header-icon";
                image.src = "/static/images/decor/profile-human.jpg";
                image.alt = "";

                const status = document.createElement("span");
                status.className = "profile-header-status";
                status.setAttribute("aria-hidden", "true");

                profileButton.appendChild(image);
                profileButton.appendChild(status);
                profileButton.addEventListener("click", openProfileModal);

                cluster.appendChild(profileButton);
            } else {
                /* Keep grid geometry stable for non-authenticated pages. */
                const spacer = document.createElement("span");
                spacer.setAttribute("aria-hidden", "true");
                cluster.appendChild(spacer);
            }

            const divider = document.createElement("span");
            divider.className = "profile-language-divider";
            divider.setAttribute("aria-hidden", "true");

            cluster.appendChild(divider);
            cluster.appendChild(switcher);

            const cartLink =
                actions.querySelector(".cart-link-with-icon") ||
                [...actions.querySelectorAll("a")].find((link) => {
                    const label = (link.textContent || "").trim().toLowerCase();
                    try {
                        const url = new URL(link.href, window.location.origin);
                        if (/\/cart\/?$/.test(url.pathname)) return true;
                    } catch (_) {}
                    return label === "koszyk" || label === "cart";
                });

            if (cartLink) {
                cartLink.insertAdjacentElement("afterend", cluster);
            } else {
                actions.appendChild(cluster);
            }
        }

        /* User name is intentionally not shown in header anymore.
           The profile name remains inside the modal. */
        if (userChip) {
            userChip.setAttribute("aria-hidden", "true");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
