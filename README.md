# Smart Digital Gifting App

A closed-loop digital voucher marketplace for Uganda. A sender buys a gift package from a partner
store, the recipient gets a unique code by WhatsApp or SMS, and a cashier at that store verifies and
redeems it exactly once. Makerere University academic project, 2026.

**Stack:** Flask 3, SQLite, Jinja2, locally served Bootstrap 5.3 and Bootstrap Icons 1.11, vanilla JavaScript.

## Features

- Every store has a full item menu: KFC from its paper menu, most others from `store_menus.py`, with section tabs and size/option pills.
- Sweet Crumbs Bakery cake and cupcake gift products, using the existing product voucher and cashier workflow. Bakery prices are proposed demo prices pending confirmation.
- Instant search (store names and gift names) plus category chips on the homepage, with a shareable URL.
- A TF-IDF recommender at `/recommend` that searches items across all stores.
- Gift form with live validation, Ugandan phone normalisation, message counter and a live voucher preview.
- Simulated Mobile Money payment (MTN or Airtel), then a share modal: WhatsApp, SMS or copy link.
- Cashier portal: store sign-in, voucher check, one-time redemption, daily stats and an audit trail.
- Branded icon tiles when a store or product has no image; configured images fall back to the tile on load failure.
- Core Bootstrap and icon assets are served locally, with pinned CDN fallbacks; pages use system font fallbacks.

## Run it

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py                    # http://127.0.0.1:5000
```

The database (`gifting.db`) is created and seeded automatically, including under gunicorn.
Delete the file to reset the demo. Older databases from the first prototype are upgraded in place.
The KFC menu is seeded at startup; refresh it explicitly with:

```bash
flask --app app seed-kfc
flask --app app check-kfc-images
flask --app app seed-sweet-crumbs
flask --app app seed-menus
flask --app app check-images
```

The image check exits non-zero and lists any active menu items whose local image is missing.
Sweet Crumbs products are also seeded at startup through the normal catalogue seeder. Its curated
images are served from `assets/images/`; the proposed prices are not confirmed bakery prices.
The recommender accepts `GET /recommend?q=spicy%20chicken%20under%2020000` or an explicit
UGX ceiling, for example `/recommend?q=chicken&budget=20000`. It returns ranked menu items as JSON.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs session cookies. **Set this in production.** | dev-only value |
| `CASHIER_PIN` | Shared demo PIN for the cashier portal | `2026` |
| `GIFT_DB_PATH` | SQLite file location | `./gifting.db` |
| `FLASK_DEBUG` | `1` enables the debugger locally | off |
| `FLASK_ENV` | Set to `production` to enable secure session cookies (also enabled on Render/Heroku) | unset |

## Demo script for the defence (about 4 minutes)

1. Homepage: type `cake`, then `earb`. Note the "Has: ..." hint. Click a category chip.
2. Open TechHub Gadgets, choose Wireless Earbuds, enter a name, a number like `0770 123 456`, a message.
   Watch the preview voucher update. Try a bad number first to show validation.
3. Pay. The share modal shows the simulated delivery steps and the WhatsApp/SMS message.
4. Open the cashier portal from the voucher page. Sign in as **a different store** with PIN `2026`
   and try the code: it is rejected as "Wrong store" and logged.
5. Sign out, sign in as TechHub Gadgets, check the code, redeem it. Check it again: "Already redeemed".
6. Point at the audit trail and the daily stats.

## Anti-fraud design

| Threat | Defence |
|---|---|
| Guessing codes | 8 characters from a 32-letter alphabet (about 10^12 combinations), generated with `secrets`; failed lookups are rate-limited per store and client (8 misses / 5 min), and evaluated misses are logged |
| Typing errors | Alphabet excludes 0/O and 1/I; cashier input forgives case, spaces and missing hyphens |
| Double redemption | Single atomic `UPDATE ... WHERE status = 'ACTIVE'`; a second cashier gets zero rows changed |
| Cashier at the wrong store | Sign-in is per store; other stores' vouchers are rejected without revealing their details |
| Forged form posts | CSRF token on every POST |
| Script injection | Jinja auto-escaping for rendered template values |
| Disputes | Audit log of every redeem, repeat attempt, wrong-store attempt and unknown code |

Failed lookup events retain a keyed digest of the request IP for per-client rate limiting rather than the
raw IP address. This is pseudonymous data, not anonymous data; rotate `SECRET_KEY` only with awareness
that it changes the digest used for new rate-limit events.

## Project layout

```
app.py            routes, validation, security, SQLite layer, recommendations
catalogue.py      illustrative stores and gift packages
kfc_menu.py       supplied KFC Uganda menu data
seed_kfc.py       idempotent KFC menu loader and CLI seed function
templates/        Jinja2 views and shared macros
static/css/       responsive design system
static/js/        search, filters, form enhancements, sharing and confirmations
static/vendor/    pinned Bootstrap and Bootstrap Icons distributions with MIT licenses
```

Data model: `merchants` have illustrative `products` and active `menu_items`; `vouchers` reference a
merchant plus either a product or menu item and retain `price_at_purchase`. The cashier `audit_log`
records redemption outcomes, menu item, cashier label, and timestamp.

## Images

KFC menu photos are local files in `static/img/kfc/`. Missing photos render as a neutral placeholder.
Sweet Crumbs Bakery images are kept in `assets/images/` and served by the application; other
catalogue entries continue to use branded icon tiles unless an image is configured.

## Known limitations (be ready for these questions)

- Payment, SMS and WhatsApp delivery are **simulated**. Production would use the MTN MoMo / Airtel Money
  APIs and an SMS gateway such as Africa's Talking, with webhooks confirming payment before issuing codes.
- Cashier auth is one shared PIN. Production needs per-cashier accounts, hashed credentials and lockout.
- The rate limiter is SQLite-backed and identifies clients with a keyed IP digest. Deployments behind
  proxies must configure trusted proxy headers carefully; clients sharing a public IP share a bucket,
  and distributed abuse needs a shared rate-limit service and monitoring.
- KFC menu entries and prices are demo data sourced from the supplied KFC Uganda menu; prices may vary
  by branch. Smart Gifting is not affiliated with KFC. Other store names and package prices are illustrative.
- Voucher links are bearer links: anyone holding the code can use it, as with physical gift cards.
- SQLite on free hosting is wiped on redeploy. Use PostgreSQL for real use.
- Store names are used for demonstration only and imply no partnership. Prices are illustrative.

## Deploy (Render)

Build command `pip install -r requirements.txt`, start command from the `Procfile`. Set `SECRET_KEY`
and `CASHIER_PIN` in the dashboard.

## Face check at pickup

When buying, the sender can choose **"Only the recipient can collect it"** (on by default).

1. The recipient opens the gift link, agrees to the consent note and does the same live scan
   (or uploads one selfie if their camera does not work). The server keeps
   only a 128-number faceprint, never the photo. The sender's own browser cannot register a face.
2. At the till, the cashier starts a **live face scan**. It runs automatically: the customer looks straight,
   turns their head left and right (random order) and looks straight again, so a printed photo or a phone
   screen cannot pass. The **Redeem** button stays locked until the face matches (or the fallback below succeeds).
3. **Fallback:** if no face was registered, the camera is not available, or the face fails three times,
   the cashier sends a one-time code to the recipient's phone (simulated SMS in the demo).
4. The faceprint is deleted as soon as the gift is collected. Every check is written to the audit trail.

Models: OpenCV YuNet (face detection) and SFace (face recognition), both pre-trained, in `ml/face/models/`.
Evaluation: `python -m ml.face.evaluate <folder>`; results in `ml/face/results.md`.

## Store menus and photos

Menus for the other stores live in `store_menus.py` (same row format as `kfc_menu.py`).
Sweet Crumbs Bakery keeps its own curated products and photos in `catalogue.py` / `assets/images/`.
Menus are seeded at startup; refresh them with `python -m flask --app app seed-menus`.

Item photos are free stock photos, downloaded on your own machine:

```powershell
pip install pillow                                  # optional, resizes to 800x600
$env:UNSPLASH_ACCESS_KEY="your-access-key"          # https://unsplash.com/developers
python fetch_images.py --source unsplash            # or --store java-house, --dry-run, --force
python -m flask --app app check-images              # lists items still missing a photo
```

Unsplash demo keys allow about 25 photos an hour; re-run the script and it skips photos it already has.
Photographer credits are saved to `static/img/credits.json` and shown at `/credits`.
Java House and Pizza Hut prices are indicative (see the notes in `store_menus.py`).
