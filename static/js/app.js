"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.querySelector("#searchForm");
    const searchInput = document.querySelector("#storeSearch");
    const clearSearch = document.querySelector("#clearSearch");
    const storeCards = Array.from(document.querySelectorAll(".store-col"));
    const categoryButtons = Array.from(document.querySelectorAll(".chip[data-cat]"));
    const resultCount = document.querySelector("#resultCount");
    const emptyState = document.querySelector("#emptyState");
    const emptyQuery = document.querySelector("#emptyQuery");
    let activeCategory = "all";

    const setUrlState = (query, category) => {
        const url = new URL(window.location.href);
        if (query) {
            url.searchParams.set("q", query);
        } else {
            url.searchParams.delete("q");
        }
        if (category !== "all") {
            url.searchParams.set("category", category);
        } else {
            url.searchParams.delete("category");
        }
        window.history.replaceState({}, "", url);
    };

    const applyStoreFilters = (writeUrl = true) => {
        if (!searchInput) {
            return;
        }

        const query = searchInput.value.trim().toLocaleLowerCase();
        let visibleCount = 0;

        storeCards.forEach((card) => {
            const categoryMatches = activeCategory === "all" || card.dataset.cat === activeCategory;
            const searchText = (card.dataset.search || "").toLocaleLowerCase();
            const searchMatches = !query || searchText.includes(query);
            const visible = categoryMatches && searchMatches;
            card.hidden = !visible;
            if (visible) {
                visibleCount += 1;
            }

            const matchHint = card.querySelector(".store-card__match");
            if (matchHint) {
                const matchingProducts = (card.dataset.products || "")
                    .split("|")
                    .filter((title) => title.toLocaleLowerCase().includes(query));
                const storeMatchesDirectly = [
                    card.dataset.cat,
                    card.querySelector(".store-card__name")?.textContent || "",
                ].some((value) => value.toLocaleLowerCase().includes(query));
                matchHint.textContent = query && matchingProducts.length && !storeMatchesDirectly
                    ? `Has: ${matchingProducts.slice(0, 3).join(", ")}${matchingProducts.length > 3 ? "…" : ""}`
                    : "";
                matchHint.hidden = !matchHint.textContent || !visible;
            }
        });

        categoryButtons.forEach((button) => {
            const selected = button.dataset.cat === activeCategory;
            button.classList.toggle("is-active", selected);
            button.setAttribute("aria-pressed", String(selected));
        });

        if (resultCount) {
            resultCount.textContent = `${visibleCount} store${visibleCount === 1 ? "" : "s"}`;
        }
        if (emptyState) {
            emptyState.hidden = visibleCount > 0;
        }
        if (emptyQuery) {
            emptyQuery.textContent = query ? `“${searchInput.value.trim()}”` : "for this category";
        }
        if (clearSearch) {
            clearSearch.hidden = !searchInput.value;
        }
        if (writeUrl) {
            setUrlState(searchInput.value.trim(), activeCategory);
        }
    };

    if (searchForm && searchInput) {
        const params = new URLSearchParams(window.location.search);
        const validCategories = categoryButtons.map((button) => button.dataset.cat);
        searchInput.value = params.get("q") || "";
        const requestedCategory = params.get("category") || "all";
        activeCategory = validCategories.includes(requestedCategory) ? requestedCategory : "all";

        searchForm.addEventListener("submit", (event) => {
            event.preventDefault();
            applyStoreFilters();
        });
        searchInput.addEventListener("input", () => applyStoreFilters());
        clearSearch?.addEventListener("click", () => {
            searchInput.value = "";
            searchInput.focus();
            applyStoreFilters();
        });
        categoryButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeCategory = button.dataset.cat || "all";
                applyStoreFilters();
            });
        });
        document.querySelector("#resetFilters")?.addEventListener("click", () => {
            searchInput.value = "";
            activeCategory = "all";
            applyStoreFilters();
            searchInput.focus();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
                const target = event.target;
                if (target instanceof HTMLElement && (
                    target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
                )) {
                    return;
                }
                event.preventDefault();
                searchInput.focus();
            } else if (event.key === "Escape" && document.activeElement === searchInput) {
                searchInput.value = "";
                applyStoreFilters();
            }
        });
        window.addEventListener("popstate", () => {
            const currentParams = new URLSearchParams(window.location.search);
            searchInput.value = currentParams.get("q") || "";
            const category = currentParams.get("category") || "all";
            activeCategory = validCategories.includes(category) ? category : "all";
            applyStoreFilters(false);
        });
        applyStoreFilters(false);
    }

    const senderName = document.querySelector("#sender_name");
    const message = document.querySelector("#message");
    const previewFrom = document.querySelector("#previewFrom");
    const previewNote = document.querySelector("#previewNote");
    const messageCount = document.querySelector("#messageCount");

    const updateGiftPreview = () => {
        if (senderName && previewFrom) {
            previewFrom.textContent = senderName.value.trim() || "you";
        }
        if (message && previewNote) {
            previewNote.textContent = message.value.trim()
                ? `“${message.value.trim()}”`
                : "Your message will appear here.";
        }
        if (message && messageCount) {
            const maxLength = Number(messageCount.dataset.max) || message.maxLength;
            messageCount.textContent = `${message.value.length} / ${maxLength}`;
            messageCount.classList.toggle("text-danger", message.value.length >= maxLength);
        }
    };

    senderName?.addEventListener("input", updateGiftPreview);
    message?.addEventListener("input", updateGiftPreview);
    updateGiftPreview();

    document.querySelectorAll(".menu-variant").forEach((select) => {
        const card = select.closest(".product-card");
        const price = card?.querySelector(".menu-price");
        const description = card?.querySelector(".menu-item-description");
        const giftButton = card?.querySelector(".menu-gift");
        const updateMenuVariant = () => {
            const option = select.selectedOptions[0];
            if (!option) {
                return;
            }
            if (price) {
                price.textContent = `UGX ${Number(option.dataset.price).toLocaleString("en-US")}`;
            }
            if (description) {
                description.textContent = option.dataset.description || "";
            }
            if (giftButton) {
                giftButton.href = option.dataset.buyUrl || "#";
            }
        };
        select.addEventListener("change", updateMenuVariant);
        updateMenuVariant();
    });

    document.querySelectorAll(".menu-variant-option").forEach((option) => {
        option.addEventListener("change", () => {
            const card = option.closest(".product-card");
            const price = card?.querySelector(".menu-price");
            const description = card?.querySelector(".menu-item-description");
            const giftButton = card?.querySelector(".menu-gift");
            if (price) {
                price.textContent = `UGX ${Number(option.dataset.price).toLocaleString("en-US")}`;
            }
            if (description && option.dataset.description) {
                description.textContent = option.dataset.description;
            }
            if (giftButton) {
                giftButton.href = option.dataset.buyUrl || "#";
            }
            const label = card?.querySelector(".price__label");
            if (label) {
                label.textContent = "Price";
            }
        });
    });

    document.querySelectorAll(".kfc-menu-tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = document.querySelector(tab.dataset.bsTarget || "");
            const tablist = tab.closest('[role="tablist"]');
            const panels = target?.parentElement?.querySelectorAll(".kfc-tab-pane");
            if (!target || !tablist || !panels) {
                return;
            }
            tablist.querySelectorAll(".kfc-menu-tab").forEach((otherTab) => {
                const selected = otherTab === tab;
                otherTab.classList.toggle("active", selected);
                otherTab.setAttribute("aria-selected", String(selected));
            });
            panels.forEach((panel) => panel.classList.remove("show", "active"));
            target.classList.add("show", "active");
            tab.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
        });
    });

    const phoneInput = document.querySelector("#recipient_phone");
    const giftForm = document.querySelector("#giftForm");
    const isUgandanMobile = (value) => {
        const digits = value.replace(/\D/g, "");
        let national = digits;
        if (digits.startsWith("256") && digits.length === 12) {
            national = digits.slice(3);
        } else if (digits.startsWith("0") && digits.length === 10) {
            national = digits.slice(1);
        }
        return /^7\d{8}$/.test(national);
    };

    if (phoneInput && giftForm) {
        const validatePhone = () => {
            const value = phoneInput.value.trim();
            phoneInput.setCustomValidity(
                !value || isUgandanMobile(value)
                    ? ""
                    : "Enter a valid Ugandan mobile number, e.g. 0770 123 456."
            );
        };
        phoneInput.addEventListener("input", validatePhone);
        phoneInput.addEventListener("blur", validatePhone);
        giftForm.addEventListener("submit", (event) => {
            validatePhone();
            giftForm.classList.add("was-validated");
            if (!giftForm.checkValidity()) {
                event.preventDefault();
                giftForm.reportValidity();
                return;
            }

            const submitButton = giftForm.querySelector('button[type="submit"]');
            const label = submitButton?.querySelector(".btn__label");
            if (submitButton && label) {
                submitButton.disabled = true;
                label.textContent = submitButton.dataset.loadingText || "Processing…";
            }
        });
    }

    document.querySelectorAll("form.needs-validation").forEach((form) => {
        form.addEventListener("submit", (event) => {
            form.classList.add("was-validated");
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                form.reportValidity();
            }
        });
    });

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }
            if (!window.confirm(form.dataset.confirm || "Continue?")) {
                event.preventDefault();
                return;
            }

            form.dataset.submitting = "true";
            const submitButton = event.submitter || form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                const label = submitButton.querySelector("[data-submit-label]");
                if (label) {
                    label.textContent = submitButton.dataset.loadingText || "Processing…";
                } else {
                    submitButton.textContent = submitButton.dataset.loadingText || "Processing…";
                }
            }
        });
    });

    document.querySelectorAll("[data-autodismiss]").forEach((alert) => {
        const delay = Number(alert.dataset.autodismiss);
        if (delay > 0 && window.bootstrap?.Alert) {
            window.setTimeout(() => window.bootstrap.Alert.getOrCreateInstance(alert).close(), delay);
        }
    });

    const autoShowModal = document.querySelector("[data-autoshow='true']");
    if (autoShowModal && window.bootstrap?.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(autoShowModal).show();
    }

    const showCopyFeedback = (messageText) => {
        const toast = document.querySelector("#copyToast");
        const toastText = document.querySelector("#copyToastText");
        if (toast && toastText && window.bootstrap?.Toast) {
            toastText.textContent = messageText;
            window.bootstrap.Toast.getOrCreateInstance(toast).show();
            return;
        }
        window.alert(messageText);
    };

    const fallbackCopy = (text) => {
        const temporaryInput = document.createElement("textarea");
        temporaryInput.value = text;
        temporaryInput.setAttribute("readonly", "");
        temporaryInput.style.position = "fixed";
        temporaryInput.style.opacity = "0";
        document.body.append(temporaryInput);
        temporaryInput.select();
        let copied = false;
        try {
            copied = document.execCommand("copy");
        } finally {
            temporaryInput.remove();
        }
        return copied;
    };

    document.querySelectorAll("[data-copy]").forEach((button) => {
        const label = button.querySelector("span") || button;
        const originalLabel = label.textContent;
        const originalClasses = button.className;
        let resetTimer;

        button.addEventListener("click", async () => {
            const value = button.dataset.copy || "";
            const copyLabel = button.dataset.copyLabel || "Copy";
            let copied = false;
            try {
                if (navigator.clipboard?.writeText) {
                    await navigator.clipboard.writeText(value);
                    copied = true;
                } else {
                    copied = fallbackCopy(value);
                }
            } catch {
                copied = fallbackCopy(value);
            }
            if (copied) {
                label.textContent = "Copied!";
                button.classList.add("btn-success");
                button.classList.remove("btn-outline-dark", "btn-light");
                window.clearTimeout(resetTimer);
                resetTimer = window.setTimeout(() => {
                    label.textContent = originalLabel;
                    button.className = originalClasses;
                }, 1800);
            }
            showCopyFeedback(
                copied
                    ? `${copyLabel.replace(/^Copy\s+/i, "")} copied`
                    : "Copy failed. Please select and copy manually."
            );
        });
    });
});
