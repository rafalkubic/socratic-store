(() => {
    const modal = document.getElementById("conversationProfileModal");
    if (!modal) return;

    const closeButton = modal.querySelector(".conversation-profile-close");
    const userName = (modal.dataset.profileUser || "").trim();
    let lastFocused = null;

    const STORAGE_KEY = "socratic_store_conversation_profile_v1";

    const translations = {
        pl: {
            dominant: "Dominujący kontekst",
            hylik: "Hylik · filozofia",
            psychik: "Psychik · psychologia",
            pneumatyk: "Pneumatyk · teologia",
            observations: "Liczba obserwacji",
            adapt: "Adaptuj rozmowę Socratic AI do tego profilu",
            save: "Zapisz",
            reset: "Wyzeruj wagi profilu",
            saved: "Profil zapisany lokalnie.",
            resetDone: "Wagi profilu wyzerowane.",
            none: "Brak"
        },
        en: {
            dominant: "Dominant context",
            hylik: "Hylic · philosophy",
            psychik: "Psychic · psychology",
            pneumatyk: "Pneumatic · theology",
            observations: "Observation count",
            adapt: "Adapt Socratic AI conversation to this profile",
            save: "Save",
            reset: "Reset profile weights",
            saved: "Profile saved locally.",
            resetDone: "Profile weights reset.",
            none: "None"
        }
    };

    const lang = (document.documentElement.lang || "pl").toLowerCase().startsWith("en") ? "en" : "pl";
    const t = translations[lang];

    const clampPct = (value) => {
        const n = Number(value);
        if (!Number.isFinite(n)) return 0;
        return Math.max(0, Math.min(100, n));
    };

    const normalizeProfile = (raw = {}) => {
        const sourceWeights = raw.weights || raw;
        return {
            hylik: clampPct(sourceWeights.hylik ?? sourceWeights.hylic ?? 19.5),
            psychik: clampPct(sourceWeights.psychik ?? sourceWeights.psychic ?? 17.4),
            pneumatyk: clampPct(sourceWeights.pneumatyk ?? sourceWeights.pneumatic ?? 63.1),
            observations: Math.max(0, Number.parseInt(raw.observations ?? raw.observation_count ?? 3, 10) || 0),
            adapt: raw.adapt !== false
        };
    };

    const loadProfile = () => {
        // Future integration hook: Socratic AI can inject current profile data.
        if (window.SOCRATIC_PROFILE && typeof window.SOCRATIC_PROFILE === "object") {
            return normalizeProfile(window.SOCRATIC_PROFILE);
        }

        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) return normalizeProfile(JSON.parse(stored));
        } catch (_) {}

        return normalizeProfile();
    };

    let profile = loadProfile();

    const dominantKey = () => {
        const entries = [
            ["Hylik", profile.hylik],
            ["Psychik", profile.psychik],
            ["Pneumatyk", profile.pneumatyk]
        ];
        const max = Math.max(...entries.map(([, value]) => value));
        if (max <= 0) return t.none;
        return entries.find(([, value]) => value === max)?.[0] || t.none;
    };

    const detailsMarkup = `
        <div class="conversation-profile-details" data-profile-details>
            <div class="profile-dominant-row">
                <span class="profile-dominant-label">${t.dominant}</span>
                <strong class="profile-dominant-value" data-profile-dominant></strong>
            </div>

            <div class="profile-weight-list">
                <div class="profile-weight-item" data-weight-key="hylik">
                    <div class="profile-weight-head">
                        <span class="profile-weight-label">${t.hylik}</span>
                        <strong class="profile-weight-value" data-weight-value></strong>
                    </div>
                    <div class="profile-weight-track" aria-hidden="true">
                        <span class="profile-weight-fill" data-weight-fill></span>
                    </div>
                </div>

                <div class="profile-weight-item" data-weight-key="psychik">
                    <div class="profile-weight-head">
                        <span class="profile-weight-label">${t.psychik}</span>
                        <strong class="profile-weight-value" data-weight-value></strong>
                    </div>
                    <div class="profile-weight-track" aria-hidden="true">
                        <span class="profile-weight-fill" data-weight-fill></span>
                    </div>
                </div>

                <div class="profile-weight-item" data-weight-key="pneumatyk">
                    <div class="profile-weight-head">
                        <span class="profile-weight-label">${t.pneumatyk}</span>
                        <strong class="profile-weight-value" data-weight-value></strong>
                    </div>
                    <div class="profile-weight-track" aria-hidden="true">
                        <span class="profile-weight-fill" data-weight-fill></span>
                    </div>
                </div>
            </div>

            <p class="profile-observations">
                ${t.observations}: <strong data-profile-observations></strong>
            </p>

            <div class="profile-controls">
                <label class="profile-adapt-label">
                    <input type="checkbox" class="profile-adapt-checkbox" data-profile-adapt>
                    <span>${t.adapt}</span>
                </label>

                <button class="profile-button profile-save" type="button" data-profile-save>${t.save}</button>
                <button class="profile-button profile-reset" type="button" data-profile-reset>${t.reset}</button>
                <span class="profile-status" data-profile-status aria-live="polite"></span>
            </div>
        </div>
    `;

    const content = modal.querySelector(".conversation-profile-content");
    if (content && !content.querySelector("[data-profile-details]")) {
        content.insertAdjacentHTML("beforeend", detailsMarkup);
    }

    const status = modal.querySelector("[data-profile-status]");
    const adaptCheckbox = modal.querySelector("[data-profile-adapt]");

    const render = () => {
        modal.querySelector("[data-profile-dominant]").textContent = dominantKey();
        modal.querySelector("[data-profile-observations]").textContent = String(profile.observations);

        modal.querySelectorAll("[data-weight-key]").forEach((item) => {
            const key = item.dataset.weightKey;
            const value = clampPct(profile[key]);
            item.querySelector("[data-weight-value]").textContent = `${value.toFixed(1)}%`;
            item.querySelector("[data-weight-fill]").style.width = `${value}%`;
        });

        if (adaptCheckbox) adaptCheckbox.checked = Boolean(profile.adapt);
    };

    const persist = () => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
        } catch (_) {}
    };

    const setStatus = (message) => {
        if (!status) return;
        status.textContent = message;
        window.clearTimeout(setStatus.timer);
        setStatus.timer = window.setTimeout(() => {
            status.textContent = "";
        }, 2800);
    };

    modal.querySelector("[data-profile-save]")?.addEventListener("click", () => {
        profile.adapt = Boolean(adaptCheckbox?.checked);
        persist();
        window.dispatchEvent(new CustomEvent("socratic-profile-save", {
            detail: { ...profile, user: userName }
        }));
        setStatus(t.saved);
    });

    modal.querySelector("[data-profile-reset]")?.addEventListener("click", () => {
        profile.hylik = 0;
        profile.psychik = 0;
        profile.pneumatyk = 0;
        profile.adapt = Boolean(adaptCheckbox?.checked);
        persist();
        render();
        window.dispatchEvent(new CustomEvent("socratic-profile-reset", {
            detail: { ...profile, user: userName }
        }));
        setStatus(t.resetDone);
    });

    adaptCheckbox?.addEventListener("change", () => {
        profile.adapt = Boolean(adaptCheckbox.checked);
    });

    render();

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
        opener.setAttribute("role", "button");
        if (!opener.hasAttribute("tabindex") && opener.tagName !== "BUTTON" && opener.tagName !== "A") {
            opener.setAttribute("tabindex", "0");
        }
        opener.setAttribute("aria-haspopup", "dialog");
        opener.setAttribute("aria-controls", "conversationProfileModal");
        opener.addEventListener("click", (event) => {
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
