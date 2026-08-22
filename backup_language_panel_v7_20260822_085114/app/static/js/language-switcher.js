(() => {
    function initLanguageSwitcher() {
        const switcher = document.querySelector(".language-switcher");
        if (!switcher || switcher.classList.contains("language-menu-ready")) return;

        const links = [...switcher.querySelectorAll("a")];
        if (!links.length) return;

        const getLang = (link) => {
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

        const options = {};
        links.forEach((link) => {
            const lang = getLang(link);
            if (lang) options[lang] = link.href;
        });

        if (!options.PL || !options.EN) return;

        const htmlLang = (document.documentElement.lang || "pl").toUpperCase();
        let current = htmlLang.startsWith("EN") ? "EN" : "PL";

        const activeLink = links.find((link) => link.classList.contains("active"));
        if (activeLink) {
            const activeLang = getLang(activeLink);
            if (activeLang) current = activeLang;
        }

        switcher.classList.add("language-menu-ready");

        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "language-menu-trigger";
        trigger.setAttribute("aria-haspopup", "menu");
        trigger.setAttribute("aria-expanded", "false");
        trigger.setAttribute("aria-controls", "languageMenu");
        trigger.textContent = current;

        const menu = document.createElement("div");
        menu.id = "languageMenu";
        menu.className = "language-menu";
        menu.setAttribute("role", "menu");
        menu.hidden = true;

        ["EN", "PL"].forEach((lang) => {
            const option = document.createElement("a");
            option.href = options[lang];
            option.className = "language-menu-option";
            option.setAttribute("role", "menuitemradio");
            option.setAttribute("aria-checked", lang === current ? "true" : "false");
            option.dataset.lang = lang;

            if (lang === current) option.classList.add("is-active");

            option.innerHTML = `
                <span class="language-menu-radio" aria-hidden="true"></span>
                <span class="language-menu-option-text">${lang}</span>
            `;

            menu.appendChild(option);
        });

        switcher.appendChild(trigger);
        switcher.appendChild(menu);

        const setOpen = (open) => {
            menu.hidden = !open;
            trigger.setAttribute("aria-expanded", open ? "true" : "false");
        };

        trigger.addEventListener("click", (event) => {
            event.stopPropagation();
            setOpen(menu.hidden);
        });

        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });

        document.addEventListener("click", () => setOpen(false));

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !menu.hidden) {
                setOpen(false);
                trigger.focus();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLanguageSwitcher, { once: true });
    } else {
        initLanguageSwitcher();
    }
})();
