(() => {
    const CONTEXT_WORDS = [
        "hylik", "psychik", "pneumatyk",
        "hylic", "psychic", "pneumatic"
    ];

    const contextOnlyPattern = new RegExp(
        "^[·•\\-–—:\\s]*(?:" + CONTEXT_WORDS.join("|") + ")[\\s]*$",
        "i"
    );

    const contextSuffixPattern = new RegExp(
        "\\s*[·•|/\\-–—:]\\s*(?:" + CONTEXT_WORDS.join("|") + ")\\s*$",
        "i"
    );

    let cleaning = false;

    function isCartLink(link) {
        if (!link) return false;

        try {
            const url = new URL(link.href, window.location.origin);
            if (/\/cart\/?$/.test(url.pathname)) return true;
        } catch (_) {}

        const label = (link.textContent || "").trim().toLowerCase();
        return label === "koszyk" || label === "cart";
    }

    function cleanupHeader() {
        if (cleaning) return;
        cleaning = true;

        try {
            const header = document.querySelector(".site-header");
            if (!header) return;

            // Remove the old "Back to Socratic AI" navigation element.
            header.querySelectorAll(".ghost-link").forEach((element) => element.remove());

            const actions = header.querySelector(".header-actions");
            if (!actions) return;

            // Add the gold shopping-bag icon to the cart link.
            [...actions.querySelectorAll("a")].forEach((link) => {
                if (isCartLink(link)) {
                    link.classList.add("cart-link-with-icon");
                }
            });

            // Keep the user name, but remove an appended context such as
            // "Rafal · pneumatyk" if an older integration added it.
            actions.querySelectorAll(".user-chip").forEach((chip) => {
                const original = (chip.textContent || "").trim();
                const cleaned = original.replace(contextSuffixPattern, "").trim();

                if (cleaned && cleaned !== original) {
                    chip.textContent = cleaned;
                }
            });

            // Remove a separate nearby badge/text node containing only
            // hylik / psychik / pneumatyk (and English equivalents).
            [...actions.children].forEach((element) => {
                if (element.classList.contains("user-chip")) return;
                if (element.classList.contains("language-switcher")) return;

                const text = (element.textContent || "").trim();

                if (contextOnlyPattern.test(text)) {
                    element.remove();
                    return;
                }

                // Handle wrappers like "<span>· pneumatyk</span>".
                if (
                    element.children.length === 0 &&
                    CONTEXT_WORDS.some((word) => text.toLowerCase().includes(word)) &&
                    text.length <= 24
                ) {
                    element.remove();
                }
            });

            // Also inspect text nodes directly inside header-actions.
            [...actions.childNodes].forEach((node) => {
                if (node.nodeType !== Node.TEXT_NODE) return;

                const text = (node.textContent || "").trim();
                if (contextOnlyPattern.test(text)) {
                    node.remove();
                }
            });
        } finally {
            cleaning = false;
        }
    }

    function init() {
        cleanupHeader();

        const actions = document.querySelector(".header-actions");
        if (!actions) return;

        const observer = new MutationObserver(() => {
            window.requestAnimationFrame(cleanupHeader);
        });

        observer.observe(actions, {
            childList: true,
            subtree: true,
            characterData: true
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
