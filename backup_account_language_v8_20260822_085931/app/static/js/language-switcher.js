(() => {
    function initLanguagePanel() {
        const switcher = document.querySelector(".language-switcher");
        if (!switcher) return;

        const originalLinks = [...switcher.querySelectorAll("a")];

        const detectLang = (link) => {
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

        const destinations = {};

        originalLinks.forEach((link) => {
            const lang = detectLang(link);
            if (lang && !destinations[lang]) {
                destinations[lang] = link.href;
            }
        });

        if (!destinations.PL || !destinations.EN) return;

        let current = (document.documentElement.lang || "pl")
            .toUpperCase()
            .startsWith("EN") ? "EN" : "PL";

        const activeOriginal = originalLinks.find((link) => link.classList.contains("active"));
        if (activeOriginal) {
            const lang = detectLang(activeOriginal);
            if (lang) current = lang;
        }

        // Remove any V6 dropdown UI previously generated in this DOM.
        switcher.querySelectorAll(
            ".language-menu-trigger, .language-menu, .language-inline-option"
        ).forEach((element) => element.remove());

        switcher.classList.remove("language-menu-ready");
        switcher.classList.add("language-panel-ready");

        // Socratic AI visual order from the supplied reference: EN above, PL below.
        ["EN", "PL"].forEach((lang) => {
            const option = document.createElement("a");
            option.href = destinations[lang];
            option.className = "language-inline-option";
            option.setAttribute("role", "radio");
            option.setAttribute("aria-checked", lang === current ? "true" : "false");
            option.setAttribute("aria-label", lang === "PL" ? "Polski" : "English");

            if (lang === current) option.classList.add("is-active");

            const radio = document.createElement("span");
            radio.className = "language-inline-radio";
            radio.setAttribute("aria-hidden", "true");

            const label = document.createElement("span");
            label.className = "language-inline-option-text";
            label.textContent = lang;

            option.appendChild(radio);
            option.appendChild(label);
            switcher.appendChild(option);
        });

        switcher.setAttribute("role", "radiogroup");
        switcher.setAttribute("aria-label", "Language");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLanguagePanel, { once: true });
    } else {
        initLanguagePanel();
    }
})();
