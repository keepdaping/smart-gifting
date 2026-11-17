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
        const col = el("div", "col-6");
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
            recs.forEach((rec, i) => {
                const node = card(rec);
                node.style.setProperty("--i", i);
                results.append(node);
            });
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
    const panel = document.getElementById("giftFinder");
    const fab = document.querySelector(".finder-fab");

    // A small speech bubble above the button, shown once per visit on the homepage.
    let teaser = null;
    const hideTeaser = () => {
        if (!teaser) {
            return;
        }
        const node = teaser;
        teaser = null;
        node.classList.add("is-leaving");
        node.addEventListener("animationend", () => node.remove(), { once: true });
        setTimeout(() => node.remove(), 500);
    };
    const seen = () => {
        try { return sessionStorage.getItem("sgFinderTeaser") === "1"; } catch (e) { return true; }
    };
    const markSeen = () => {
        try { sessionStorage.setItem("sgFinderTeaser", "1"); } catch (e) { /* storage blocked: show again next time */ }
    };
    if (fab && panel && window.location.pathname === "/" && !seen()) {
        setTimeout(() => {
            if (panel.classList.contains("show")) {
                return;
            }
            teaser = document.createElement("button");
            teaser.type = "button";
            teaser.className = "finder-teaser";
            teaser.innerHTML = "<strong>Not sure what to get?</strong><br>Tell me who it's for and your budget.";
            teaser.addEventListener("click", () => {
                window.bootstrap && window.bootstrap.Offcanvas.getOrCreateInstance(panel).show();
            });
            document.body.append(teaser);
            markSeen();
            setTimeout(hideTeaser, 7000);
        }, 3500);
    }
    if (panel) {
        panel.addEventListener("show.bs.offcanvas", hideTeaser);
    }

    if (panel && window.bootstrap) {
        panel.addEventListener("shown.bs.offcanvas", () => input.focus());
        if (window.location.hash === "#giftFinder") {
            window.bootstrap.Offcanvas.getOrCreateInstance(panel).show();
        }
    }
    document.querySelectorAll("[data-finder-q]").forEach((chip) => {
        chip.addEventListener("click", () => {
            input.value = chip.dataset.finderQ;
            run(input.value);
        });
    });
})();


/* Face check: camera capture for the recipient (register) and the cashier (check).
   Photos are resized in the browser and sent once; the server keeps only a faceprint. */
(() => {
    const MAX_SIDE = 640;

    const toJpeg = (source, width, height) => new Promise((resolve) => {
        const scale = Math.min(1, MAX_SIDE / Math.max(width, height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(width * scale);
        canvas.height = Math.round(height * scale);
        canvas.getContext("2d").drawImage(source, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(resolve, "image/jpeg", 0.85);
    });

    document.querySelectorAll("[data-face-capture]").forEach((box) => {
        const cam = box.querySelector(".face-cam");
        const video = box.querySelector("video");
        const start = box.querySelector("[data-face-start]");
        const shoot = box.querySelector("[data-face-shoot]");
        const file = box.querySelector("[data-face-file]");
        const msg = box.querySelector(".face-msg");
        const consent = box.dataset.requireConsent ? document.querySelector(box.dataset.requireConsent) : null;
        let stream = null;

        const say = (text, tone) => {
            msg.textContent = text;
            msg.className = `face-msg small mt-2 mb-0${tone ? ` text-${tone}` : ""}`;
        };
        const stop = () => {
            if (stream) {
                stream.getTracks().forEach((t) => t.stop());
                stream = null;
            }
        };
        const needsConsent = () => {
            if (consent && !consent.checked) {
                say("Please tick the box to agree first.", "danger");
                consent.focus();
                return true;
            }
            return false;
        };

        const send = async (blob) => {
            if (!blob) {
                say("The photo could not be taken. Please try again.", "danger");
                return;
            }
            const data = new FormData();
            box.querySelectorAll("input[name]").forEach((input) => {
                if (input.type === "checkbox" && !input.checked) {
                    return;
                }
                if (input.type !== "file") {
                    data.append(input.name, input.value);
                }
            });
            data.append("photo", blob, "face.jpg");
            [shoot, start].forEach((b) => b && (b.disabled = true));
            say("Checking the photo…");
            try {
                const response = await fetch(box.dataset.endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } });
                const result = await response.json().catch(() => ({}));
                const good = response.ok && result.ok && result.matched !== false;
                say(result.message || (good ? "Done." : "Something went wrong. Please try again."), good ? "success" : "danger");
                if (good || result.attempts_left === 0) {
                    stop();
                    if (cam) {
                        cam.hidden = true;
                    }
                    if (shoot) {
                        shoot.hidden = true;
                    }
                    if (box.dataset.successReload) {
                        setTimeout(() => window.location.reload(), good ? 900 : 1600);
                    }
                }
            } catch (error) {
                say("Could not reach the server. Check the connection and try again.", "danger");
            } finally {
                [shoot, start].forEach((b) => b && (b.disabled = false));
            }
        };

        start && start.addEventListener("click", async () => {
            if (needsConsent()) {
                return;
            }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                say("This browser cannot open the camera here. Choose a selfie instead.", "danger");
                return;
            }
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 } }, audio: false });
                video.srcObject = stream;
                cam.hidden = false;
                start.hidden = true;
                shoot.hidden = false;
                say("Look straight at the camera in good light, then press the button.");
            } catch (error) {
                say("The camera could not be opened. Allow camera access, or choose a selfie instead.", "danger");
            }
        });

        shoot && shoot.addEventListener("click", async () => {
            if (needsConsent() || !video.videoWidth) {
                return;
            }
            send(await toJpeg(video, video.videoWidth, video.videoHeight));
        });

        file && file.addEventListener("change", async () => {
            const picked = file.files && file.files[0];
            file.value = "";
            if (!picked || needsConsent()) {
                return;
            }
            const image = new Image();
            image.onload = async () => {
                URL.revokeObjectURL(image.src);
                send(await toJpeg(image, image.naturalWidth, image.naturalHeight));
            };
            image.onerror = () => say("That file is not a photo. Choose a selfie.", "danger");
            image.src = URL.createObjectURL(picked);
        });

        window.addEventListener("pagehide", stop);
    });
})();



/* Live face scan: scans automatically and asks the person to turn their head,
   so a printed photo or a phone screen cannot pass. One small frame is sent about
   three times a second; the server decides when each step is done. */
(() => {
    const LABELS = { center: "Straight", left: "Left", right: "Right", final: "Straight" };
    const FRAME_SIDE = 400;
    const FRAME_GAP_MS = 280;

    document.querySelectorAll("[data-face-live]").forEach((box) => {
        const cam = box.querySelector(".face-cam");
        const video = box.querySelector("video");
        const prompt = box.querySelector(".face-cam__prompt");
        const arrow = box.querySelector(".face-cam__arrow");
        const stepsList = box.querySelector(".face-steps");
        const start = box.querySelector("[data-face-start]");
        const msg = box.querySelector(".face-msg");
        const consent = box.dataset.requireConsent ? document.querySelector(box.dataset.requireConsent) : null;
        const canvas = document.createElement("canvas");
        let stream = null;
        let running = false;
        let steps = [];

        const field = (name) => (box.querySelector(`input[name="${name}"]`) || {}).value || "";
        const say = (text, tone) => {
            msg.textContent = text || "";
            msg.className = `face-msg small mt-2 mb-0${tone ? ` text-${tone}` : ""}`;
        };
        const stop = () => {
            running = false;
            if (stream) {
                stream.getTracks().forEach((t) => t.stop());
                stream = null;
            }
        };
        const showSteps = (current) => {
            stepsList.replaceChildren(...steps.map((step, i) => {
                const li = document.createElement("li");
                li.textContent = LABELS[step];
                li.className = i < current ? "is-done" : (i === current ? "is-current" : "");
                return li;
            }));
            stepsList.hidden = false;
            const step = steps[current];
            const turning = step === "left" || step === "right";
            arrow.hidden = !turning;
            // The preview is mirrored, so the person's left is on the left of the screen.
            arrow.className = `face-cam__arrow${turning ? ` face-cam__arrow--${step}` : ""}`;
            arrow.firstElementChild.className = `bi bi-arrow-${step === "right" ? "right" : "left"}`;
            cam.dataset.step = step || "";
        };
        const post = async (url, extra) => {
            const data = new FormData();
            data.append("csrf_token", field("csrf_token"));
            Object.entries(extra).forEach(([k, v]) => data.append(k, v));
            const response = await fetch(url, { method: "POST", body: data, headers: { Accept: "application/json" } });
            const result = await response.json().catch(() => ({ ok: false, message: "Something went wrong. Please try again." }));
            return { response, result };
        };
        const grab = () => new Promise((resolve) => {
            const w = video.videoWidth;
            const h = video.videoHeight;
            const scale = Math.min(1, FRAME_SIDE / Math.max(w, h));
            canvas.width = Math.round(w * scale);
            canvas.height = Math.round(h * scale);
            canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(resolve, "image/jpeg", 0.75);
        });

        const begin = async () => {
            const { result } = await post(box.dataset.startUrl, {
                purpose: field("purpose"), voucher_code: field("voucher_code"),
                consent: consent && consent.checked ? "yes" : "",
            });
            if (!result.ok) {
                stop();
                cam.hidden = true;
                start.hidden = false;
                say(result.message, "danger");
                return false;
            }
            steps = result.steps;
            showSteps(0);
            prompt.textContent = result.prompt;
            say("");
            return true;
        };

        const loop = async () => {
            while (running) {
                const started = performance.now();
                if (video.videoWidth) {
                    const blob = await grab();
                    let reply;
                    try {
                        const data = new FormData();
                        data.append("csrf_token", field("csrf_token"));
                        data.append("photo", blob, "frame.jpg");
                        const response = await fetch(box.dataset.frameUrl, { method: "POST", body: data, headers: { Accept: "application/json" } });
                        reply = await response.json().catch(() => ({ ok: false, message: "Something went wrong." }));
                    } catch (error) {
                        reply = { ok: true, prompt: "Connection is slow… keep still." };
                    }
                    if (!running) {
                        return;
                    }
                    if (reply.restart) {
                        prompt.textContent = reply.message;
                        await new Promise((r) => setTimeout(r, 1400));
                        if (!running || !(await begin())) {
                            return;
                        }
                        continue;
                    }
                    if (reply.done) {
                        const good = reply.ok && reply.matched !== false;
                        stop();
                        showSteps(steps.length);
                        cam.classList.add(good ? "face-cam--ok" : "face-cam--bad");
                        prompt.textContent = good ? "✓" : "✗";
                        say(reply.message, good ? "success" : "danger");
                        setTimeout(() => window.location.reload(), good ? 1100 : 2000);
                        return;
                    }
                    if (!reply.ok) {
                        stop();
                        say(reply.message, "danger");
                        return;
                    }
                    if (typeof reply.step === "number") {
                        showSteps(reply.step);
                    }
                    prompt.textContent = reply.prompt || "";
                }
                const wait = FRAME_GAP_MS - (performance.now() - started);
                if (wait > 0) {
                    await new Promise((r) => setTimeout(r, wait));
                }
            }
        };

        start.addEventListener("click", async () => {
            if (consent && !consent.checked) {
                say("Please tick the box to agree first.", "danger");
                consent.focus();
                return;
            }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                say("This browser cannot open the camera here.", "danger");
                return;
            }
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 640 } }, audio: false });
            } catch (error) {
                say("The camera could not be opened. Allow camera access and try again.", "danger");
                return;
            }
            video.srcObject = stream;
            cam.hidden = false;
            cam.classList.remove("face-cam--ok", "face-cam--bad");
            start.hidden = true;
            if (await begin()) {
                running = true;
                loop();
            }
        });

        window.addEventListener("pagehide", stop);
    });
})();
