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


/* AI gift finder: sends the request to /recommend and shows the ranked gifts. */
(() => {
    const form = document.getElementById("finderForm");
    if (!form) {
        return;
    }
    const input = document.getElementById("finderInput");
    const status = document.getElementById("finderStatus");
    const results = document.getElementById("finderResults");
    const button = form.querySelector(".finder__go");
    const spinner = button.querySelector(".spinner-border");
    const ugx = (n) => `UGX ${Number(n).toLocaleString("en-US")}`;
    let lastRequest = 0;

    const el = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    };

    const card = (rec) => {
        const col = el("div", "col-12 col-sm-6 col-lg-3");
        const article = el("article", "product-card finder-card");
        const media = el("div", "media-tile media-tile--menu");
        media.setAttribute("role", "img");
        media.setAttribute("aria-label", rec.item.name);
        const fallback = el("span", "media-tile__fallback");
        fallback.setAttribute("aria-hidden", "true");
        fallback.append(el("i", "bi bi-gift"), el("span", "", rec.item.name));
        media.append(fallback);
        if (rec.image) {
            const img = el("img");
            img.src = rec.image;
            img.alt = "";
            img.loading = "lazy";
            img.addEventListener("error", () => img.remove());
            media.append(img);
        }

        const body = el("div", "product-card__body");
        body.append(el("p", "finder-card__store", rec.merchant.name));
        const title = rec.item.variant ? `${rec.item.name} (${rec.item.variant})` : rec.item.name;
        body.append(el("h3", "product-card__title", title));
        if (rec.item.description) {
            body.append(el("p", "product-card__desc", rec.item.description));
        }
        const foot = el("div", "product-card__foot");
        const price = el("span", "price");
        price.append(el("span", "menu-price", ugx(rec.price)));
        const link = el("a", "btn btn-primary btn-sm px-3");
        link.href = rec.buy_url;
        link.append(el("i", "bi bi-gift me-1"), document.createTextNode("Gift this"));
        foot.append(price, link);
        body.append(foot);
        article.append(media, body);
        col.append(article);
        return col;
    };

    const setBusy = (busy) => {
        button.disabled = busy;
        spinner.hidden = !busy;
        results.setAttribute("aria-busy", busy ? "true" : "false");
    };

    const run = async (query) => {
        query = query.trim();
        if (!query) {
            status.textContent = "Describe who the gift is for, for example “coffee for a friend”.";
            input.focus();
            return;
        }
        const requestId = ++lastRequest;
        setBusy(true);
        status.textContent = "Finding gifts…";
        try {
            const response = await fetch(`/recommend?q=${encodeURIComponent(query)}`, {
                headers: { Accept: "application/json" },
                signal: AbortSignal.timeout ? AbortSignal.timeout(20000) : undefined,
            });
            const data = await response.json();
            if (requestId !== lastRequest) {
                return;
            }
            results.replaceChildren();
            if (!response.ok) {
                status.textContent = data.error || "The gift finder could not read that request. Try different words.";
                return;
            }
            const recs = (data.recommendations || []).slice(0, 8);
            if (!recs.length) {
                status.textContent = `No gifts matched “${query}”${data.budget ? ` within ${ugx(data.budget)}` : ""}. ` +
                    "Try naming a person, an occasion or an item, like “cake for a birthday”.";
                return;
            }
            const stores = new Set(recs.map((r) => r.merchant.name)).size;
            status.textContent = `${recs.length} gift${recs.length === 1 ? "" : "s"} from ${stores} store${stores === 1 ? "" : "s"}` +
                (data.budget ? `, all within ${ugx(data.budget)}.` : ".");
            recs.forEach((rec) => results.append(card(rec)));
        } catch (error) {
            if (requestId === lastRequest) {
                status.textContent = error && error.name === "TimeoutError"
                    ? "The gift finder took too long to answer. Try again in a moment."
                    : "The gift finder is not responding. Check that the app is running, then try again.";
            }
        } finally {
            if (requestId === lastRequest) {
                setBusy(false);
            }
        }
    };

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        run(input.value);
    });
    document.querySelectorAll("[data-finder-q]").forEach((chip) => {
        chip.addEventListener("click", () => {
            input.value = chip.dataset.finderQ;
            run(input.value);
        });
    });
})();
