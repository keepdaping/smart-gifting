"""Smart Digital Gifting App - Flask application.

A closed-loop digital voucher marketplace. A sender buys a gift package from a
partner store, the recipient receives a unique code (via SMS / WhatsApp), and a
cashier at that store verifies and redeems the code exactly once.

Architecture
------------
* ``catalogue.py``  - partner stores and gift packages (seed data).
* ``kfc_menu.py`` / ``store_menus.py`` - item menus for every store.
* ``app.py``        - routes, validation, security and the SQLite data layer.
* ``templates/``    - Jinja2 views (Bootstrap 5 plus ``static/css/app.css``).
* ``static/js/``    - progressive enhancement (search, validation, share modal).

Anti-fraud design (the core of the project)
-------------------------------------------
1. Codes are generated with ``secrets`` (cryptographically secure), 8 characters
   from an alphabet without look-alike characters (no 0/O or 1/I).
2. Redemption is a single atomic ``UPDATE ... WHERE status = 'ACTIVE'`` so two
   cashiers cannot redeem the same voucher at the same moment.
3. The cashier portal needs a store + PIN, and a cashier can only redeem vouchers
   that belong to their own store.
4. Every verification outcome (redeemed, already used, wrong store, not found) is
   written to an audit log shown in the portal, and repeated wrong guesses are
   rate-limited.
"""

import hashlib
import hmac
import math
import os
import re
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import click
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, send_file,
                   request, send_from_directory, session, url_for)
from markupsafe import Markup, escape
from werkzeug.middleware.proxy_fix import ProxyFix

from catalogue import MERCHANTS, image_url
from store_menus import STORE_MENUS

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
# Render / Heroku terminate HTTPS at a proxy; trust one hop so url_for(_external=True)
# produces correct https:// links in the share message.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    DATABASE=os.environ.get("GIFT_DB_PATH", str(BASE_DIR / "gifting.db")),
    CASHIER_PIN=os.environ.get("CASHIER_PIN", "2026"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("FLASK_ENV", "").lower() == "production"
        or bool(os.environ.get("RENDER"))
        or bool(os.environ.get("DYNO"))
    ),
    MAX_CONTENT_LENGTH=64 * 1024,  # forms here are tiny; reject anything larger
)

if app.config["SECRET_KEY"] == "dev-only-change-me" and os.environ.get("RENDER"):
    print("WARNING: SECRET_KEY is not set. Set it in your hosting dashboard.")

EAT = timezone(timedelta(hours=3))  # East Africa Time (no daylight saving)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
MAX_MESSAGE_LEN = 200
MAX_FAILED_LOOKUPS = 8      # per client and store, per window
LOOKUP_WINDOW_MINUTES = 5
KFC_CATEGORIES = (
    "Wings", "Streetwise", "Burgers & Wraps", "Boxes & Strips",
    "Bucket Meals", "Buckets", "Sides", "Desserts", "Drinks",
)
SWEET_CRUMBS_PRICE_NOTICE = (
    "Proposed demo prices pending confirmation from Sweet Crumbs Bakery; "
    "these are not confirmed bakery prices."
)
KFC_NOTE = "Demo data from KFC Uganda menu. Prices may vary by branch. Not affiliated with KFC."


def store_profile(merchant_name):
    """Section order, slug and footnote for a store's menu page."""
    if merchant_name == "KFC":
        return {"slug": "kfc", "sections": list(KFC_CATEGORIES), "price_note": KFC_NOTE}
    store = STORE_MENUS.get(merchant_name, {})
    slug = store.get("slug") or re.sub(r"[^a-z0-9]+", "-", merchant_name.lower()).strip("-")
    return {
        "slug": slug,
        "sections": list(store.get("sections", [])),
        "price_note": store.get("price_note", "Demo prices for an academic project. Prices may vary in store."),
    }

PAYMENT_METHODS = {
    "mtn": "MTN Mobile Money",
    "airtel": "Airtel Money",
}

# outcome -> (label, bootstrap colour, icon)
OUTCOMES = {
    "REDEEMED": ("Redeemed", "success", "bi-check-circle-fill"),
    "ALREADY_USED": ("Already used", "warning", "bi-exclamation-triangle-fill"),
    "WRONG_STORE": ("Wrong store", "danger", "bi-shop-window"),
    "NOT_FOUND": ("Not found", "danger", "bi-question-circle-fill"),
}


# --------------------------------------------------------------------------
# Database layer
# --------------------------------------------------------------------------
def connect(path=None):
    conn = sqlite3.connect(path or app.config["DATABASE"], timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """One connection per request, closed automatically in ``close_db``."""
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _add_missing_columns(cur, table, columns):
    existing = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db(path=None):
    """Create tables and migrate older databases in place (safe to run repeatedly)."""
    conn = connect(path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            monetary_value INTEGER NOT NULL CHECK (monetary_value > 0),
            description TEXT,
            image_url TEXT,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            variant TEXT,
            description TEXT,
            price_ugx INTEGER NOT NULL CHECK (price_ugx >= 0),
            tags TEXT,
            image_filename TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            price_updated_at DATE NOT NULL DEFAULT CURRENT_DATE,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        );
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_code TEXT UNIQUE NOT NULL,
            merchant_id INTEGER NOT NULL,
            product_id INTEGER,
            menu_item_id INTEGER,
            price_at_purchase INTEGER,
            sender_name TEXT NOT NULL,
            recipient_phone TEXT NOT NULL,
            message TEXT,
            monetary_value INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'USED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_code TEXT NOT NULL,
            merchant_id INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            client_key TEXT,
            menu_item_id INTEGER,
            cashier TEXT,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        );
    """)
    cur.execute("BEGIN IMMEDIATE")
    # Columns added after the first prototype (older gifting.db files get upgraded).
    _add_missing_columns(cur, "merchants", {"image_url": "TEXT", "icon": "TEXT", "accent": "TEXT"})
    _add_missing_columns(cur, "products", {"image_url": "TEXT"})
    _add_missing_columns(cur, "vouchers", {
        "payment_method": "TEXT",
        "redeemed_at": "TIMESTAMP",
        "menu_item_id": "INTEGER REFERENCES menu_items(id)",
        "price_at_purchase": "INTEGER",
    })
    _add_missing_columns(cur, "audit_log", {
        "client_key": "TEXT",
        "menu_item_id": "INTEGER REFERENCES menu_items(id)",
        "cashier": "TEXT",
        "risk_score": "REAL",
        "risk_flag": "INTEGER",
    })

    voucher_columns = {
        row["name"]: row for row in cur.execute("PRAGMA table_info(vouchers)")
    }
    if voucher_columns["product_id"]["notnull"]:
        cur.execute("ALTER TABLE vouchers RENAME TO vouchers_legacy")
        cur.execute("""
            CREATE TABLE vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_code TEXT UNIQUE NOT NULL,
                merchant_id INTEGER NOT NULL,
                product_id INTEGER,
                menu_item_id INTEGER,
                price_at_purchase INTEGER,
                sender_name TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                message TEXT,
                monetary_value INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'USED')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_method TEXT,
                redeemed_at TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants (id),
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
            )
        """)
        cur.execute("""
            INSERT INTO vouchers (
                id, voucher_code, merchant_id, product_id, menu_item_id,
                price_at_purchase, sender_name, recipient_phone, message,
                monetary_value, status, created_at, payment_method, redeemed_at
            )
            SELECT id, voucher_code, merchant_id, product_id, menu_item_id,
                   price_at_purchase, sender_name, recipient_phone, message,
                   monetary_value, status, created_at, payment_method, redeemed_at
            FROM vouchers_legacy
        """)
        cur.execute("DROP TABLE vouchers_legacy")
    cur.execute(
        "UPDATE vouchers SET price_at_purchase = monetary_value "
        "WHERE price_at_purchase IS NULL"
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_merchant ON vouchers (merchant_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_merchant ON menu_items (merchant_id, is_active)")
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_menu_item_variant "
        "ON menu_items (merchant_id, name, COALESCE(variant, ''))"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_merchant ON audit_log (merchant_id, id)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_failures ON audit_log "
        "(merchant_id, client_key, outcome, created_at)"
    )
    for stmt in (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_merchants_name ON merchants (name)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_products_title ON products (merchant_id, title)",
    ):
        try:
            cur.execute(stmt)
        except sqlite3.IntegrityError:
            print("Note: duplicate seed rows exist in an old database; skipped unique index.")
    conn.commit()
    conn.close()


def seed_db(path=None, merchant_name=None):
    """Insert or refresh partner stores and packages (idempotent, no duplicates)."""
    conn = connect(path)
    cur = conn.cursor()
    try:
        for m in MERCHANTS:
            if merchant_name and m["name"] != merchant_name:
                continue
            row = cur.execute("SELECT id FROM merchants WHERE name = ?", (m["name"],)).fetchone()
            if not row and m["name"] == "KFC":
                row = cur.execute(
                    "SELECT id FROM merchants WHERE name = ?", ("KFC Uganda",)
                ).fetchone()
                if row:
                    cur.execute("UPDATE merchants SET name = 'KFC' WHERE id = ?", (row["id"],))
            values = (m["category"], image_url(m["photo"]), m["description"], m["icon"], m["accent"])
            if row:
                merchant_id = row["id"]
                cur.execute(
                    "UPDATE merchants SET category=?, image_url=?, description=?, icon=?, accent=? WHERE id=?",
                    values + (merchant_id,),
                )
            else:
                cur.execute(
                    "INSERT INTO merchants (category, image_url, description, icon, accent, name) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    values + (m["name"],),
                )
                merchant_id = cur.lastrowid

            for title, value, description, photo in m["products"]:
                product = cur.execute(
                    "SELECT id FROM products WHERE merchant_id = ? AND title = ?", (merchant_id, title)
                ).fetchone()
                if product:
                    cur.execute(
                        "UPDATE products SET monetary_value=?, description=?, image_url=? WHERE id=?",
                        (value, description, image_url(photo), product["id"]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO products (merchant_id, title, monetary_value, description, image_url) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (merchant_id, title, value, description, image_url(photo)),
                    )
            for title in m.get("retired_products", ()):
                product = cur.execute(
                    "SELECT id FROM products WHERE merchant_id=? AND title=?",
                    (merchant_id, title),
                ).fetchone()
                if product and not cur.execute(
                    "SELECT 1 FROM vouchers WHERE product_id=? LIMIT 1",
                    (product["id"],),
                ).fetchone():
                    cur.execute("DELETE FROM products WHERE id=?", (product["id"],))
        conn.commit()
    finally:
        conn.close()


def bootstrap(path=None):
    """Prepare the database. Runs at import so it also works under gunicorn."""
    init_db(path)
    seed_db(path)
    from seed_kfc import seed_kfc
    from seed_menus import seed_menus
    seed_kfc(path)
    seed_menus(path)


@app.cli.command("seed-kfc")
def seed_kfc_command():
    """Create/update the KFC merchant menu."""
    from seed_kfc import seed_kfc

    count = seed_kfc(app.config["DATABASE"])
    print(f"Seeded {count} KFC menu variants.")


@app.cli.command("seed-sweet-crumbs")
def seed_sweet_crumbs_command():
    """Create/update Sweet Crumbs Bakery products in the standard product catalogue."""
    seed_db(app.config["DATABASE"], merchant_name="Sweet Crumbs Bakery")
    count = get_db().execute("""
        SELECT COUNT(*) FROM products p
        JOIN merchants m ON m.id=p.merchant_id
        WHERE m.name='Sweet Crumbs Bakery'
    """).fetchone()[0]
    click.echo(f"Seeded {count} Sweet Crumbs Bakery products.")

@app.cli.command("seed-menus")
def seed_menus_command():
    """Create/update the menus of every non-KFC store."""
    from seed_menus import seed_menus

    count = seed_menus(app.config["DATABASE"])
    print(f"Seeded {count} menu variants.")


@app.cli.command("check-kfc-images")
def check_kfc_images_command():
    """Report active KFC menu items without a local image file."""
    _check_images(store="KFC")


@app.cli.command("check-images")
@click.option("--store", default=None, help="Limit the check to one store name.")
def check_images_command(store):
    """Report active menu items (all stores) without a local image file."""
    _check_images(store=store)


def _check_images(store=None):
    db = get_db()
    rows = db.execute("""
        SELECT mi.id, mi.category, mi.name, mi.variant, mi.image_filename,
               m.name AS merchant_name
        FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
        WHERE mi.is_active=1 AND (? IS NULL OR m.name = ?)
        ORDER BY m.name, mi.category, mi.name, mi.id
    """, (store, store)).fetchall()
    missing = []
    for row in rows:
        image_path = menu_image_path(row["image_filename"])
        if not image_path or not image_path.is_file():
            missing.append(row)
    if missing:
        for row in missing:
            click.echo(
                f"Missing image: {row['merchant_name']} / {row['category']} / "
                f"{row['name']} ({row['variant'] or 'standard'}): "
                f"{row['image_filename'] or '<empty>'}"
            )
        raise click.ClickException(f"{len(missing)} active menu item image(s) are missing.")
    click.echo(f"All {len(rows)} active menu item image(s) exist.")


# --------------------------------------------------------------------------
# Helpers: codes, phones, formatting
# --------------------------------------------------------------------------
def generate_voucher_code():
    """Return a code like ``GIFT-7KQM-4XPD`` using a secure random source."""
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"GIFT-{raw[:4]}-{raw[4:]}"


def normalise_code(raw):
    """Forgive spaces, lower case and missing hyphens typed by a cashier."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()
    if cleaned.startswith("GIFT"):
        cleaned = cleaned[4:]
    if len(cleaned) == 8:
        return f"GIFT-{cleaned[:4]}-{cleaned[4:]}"
    if len(cleaned) == 6:  # legacy codes from the first prototype
        return f"GIFT-{cleaned}"
    return (raw or "").strip().upper()[:24]


def normalise_phone(raw):
    """Return a Ugandan mobile number as ``+2567XXXXXXXX`` or None if invalid.

    Accepts ``0770 123 456``, ``770123456``, ``256770123456`` and ``+256 770 123 456``.
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("256") and len(digits) == 12:
        national = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        national = digits[1:]
    elif len(digits) == 9:
        national = digits
    else:
        return None
    if not re.fullmatch(r"7\d{8}", national):
        return None
    return f"+256{national}"


@app.template_filter("ugx")
def ugx_filter(value):
    return f"UGX {int(value):,}"


def menu_image_path(filename):
    """Resolve an image below static/img without accepting path traversal."""
    if not filename:
        return None
    image_root = (BASE_DIR / "static" / "img").resolve()
    image_path = (image_root / filename).resolve()
    if image_root not in image_path.parents:
        return None
    return image_path


def menu_item_image(filename):
    """Return a static URL only when the configured menu image exists."""
    image_path = menu_image_path(filename)
    if not image_path or not image_path.is_file():
        return None
    return url_for("static", filename=f"img/{filename}")


@app.template_filter("phone")
def phone_filter(value):
    normalised = normalise_phone(value)
    if not normalised:
        return value
    n = normalised[4:]
    return f"+256 {n[:3]} {n[3:6]} {n[6:]}"


@app.template_filter("eat")
def eat_filter(value, fmt="%d %b %Y, %I:%M %p"):
    """Format a stored UTC timestamp in East Africa Time."""
    if not value:
        return ""
    try:
        parsed = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return str(value)
    return parsed.astimezone(EAT).strftime(fmt)


# --------------------------------------------------------------------------
# CSRF protection and security headers
# --------------------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]


@app.before_request
def verify_csrf():
    if request.method == "POST":
        expected = session.get("_csrf", "")
        sent = request.form.get("csrf_token", "")
        if not expected or not sent or not secrets.compare_digest(expected, sent):
            abort(400)


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.context_processor
def inject_globals():
    def csrf_field():
        return Markup(f'<input type="hidden" name="csrf_token" value="{escape(csrf_token())}">')

    return {"csrf_field": csrf_field, "OUTCOMES": OUTCOMES, "cashier": session.get("cashier")}


# --------------------------------------------------------------------------
# Error pages
# --------------------------------------------------------------------------
def _error(code, title, message):
    return render_template("error.html", code=code, title=title, message=message), code


@app.errorhandler(404)
def not_found(_e):
    return _error(404, "We couldn't find that page", "The link may be mistyped, or the voucher or store no longer exists.")


@app.errorhandler(400)
def bad_request(_e):
    return _error(400, "That request didn't go through",
                  "Your session may have expired. Go back, refresh the page and try again.")


@app.errorhandler(413)
def too_large(_e):
    return _error(413, "That request was too large", "Please shorten what you entered and try again.")


@app.errorhandler(500)
def server_error(_e):
    return _error(500, "Something went wrong on our side", "Nothing was charged. Please try again in a moment.")


# --------------------------------------------------------------------------
# Public marketplace
# --------------------------------------------------------------------------
@app.route("/")
def index():
    """Store grid with data attributes the client-side search and filter read."""
    db = get_db()
    merchants = db.execute("""
        WITH menu AS (
            SELECT merchant_id,
                   COUNT(DISTINCT name) AS item_count,
                   MIN(price_ugx) AS min_price,
                   MAX(price_ugx) AS max_price,
                   REPLACE(GROUP_CONCAT(DISTINCT name), ',', '|') AS titles
            FROM menu_items WHERE is_active=1 GROUP BY merchant_id
        ),
        packs AS (
            SELECT merchant_id, COUNT(*) AS item_count, MIN(monetary_value) AS min_price,
                   MAX(monetary_value) AS max_price, GROUP_CONCAT(title, '|') AS titles
            FROM products GROUP BY merchant_id
        )
        SELECT m.*,
               COALESCE(menu.item_count, packs.item_count, 0) AS product_count,
               COALESCE(menu.min_price, packs.min_price) AS min_price,
               COALESCE(menu.max_price, packs.max_price) AS max_price,
               COALESCE(menu.titles, packs.titles) AS product_titles
        FROM merchants m
        LEFT JOIN menu ON menu.merchant_id = m.id
        LEFT JOIN packs ON packs.merchant_id = m.id
        ORDER BY m.id
    """).fetchall()
    categories = {}
    for m in merchants:
        categories[m["category"]] = categories.get(m["category"], 0) + 1
    covers = {}
    for row in db.execute(
        "SELECT merchant_id, image_filename FROM menu_items "
        "WHERE is_active=1 AND image_filename IS NOT NULL ORDER BY id"
    ):
        if row["merchant_id"] not in covers:
            image = menu_item_image(row["image_filename"])
            if image:
                covers[row["merchant_id"]] = image
    for m in merchants:
        if m["image_url"]:
            covers[m["id"]] = m["image_url"]
    return render_template("index.html", merchants=merchants, covers=covers,
                           categories=list(categories.items()))


@app.route("/assets/images/<path:filename>")
def bakery_image(filename):
    """Serve the curated bakery images without exposing other workspace files."""
    return send_from_directory(BASE_DIR / "assets" / "images", filename)


@app.route("/store/<int:merchant_id>")
def store_catalog(merchant_id):
    db = get_db()
    merchant = db.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
    if not merchant:
        abort(404)
    profile = store_profile(merchant["name"])
    rows = db.execute(
        "SELECT * FROM menu_items WHERE merchant_id=? AND is_active=1 ORDER BY id",
        (merchant_id,),
    ).fetchall()
    if rows:
        grouped = {}
        for row in rows:
            key = (row["category"], row["name"])
            if key not in grouped:
                grouped[key] = {
                    "category": row["category"],
                    "name": row["name"],
                    "description": row["description"],
                    "image": menu_item_image(row["image_filename"]),
                    "variants": [],
                }
            variant = dict(row)
            variant["image"] = menu_item_image(row["image_filename"])
            grouped[key]["variants"].append(variant)
        for item in grouped.values():
            item["variants"].sort(key=lambda v: (v["price_ugx"], v["id"]))
            item["from_price"] = item["variants"][0]["price_ugx"]
        order = profile["sections"] + sorted(
            {row["category"] for row in rows} - set(profile["sections"])
        )
        categories = []
        for category in order:
            items = [item for item in grouped.values() if item["category"] == category]
            if items:
                slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
                categories.append({"name": category, "slug": slug, "items": items})
        cover = next((item["image"] for item in grouped.values() if item["image"]), None)
        return render_template("store.html", merchant=merchant, products=[],
                               menu_categories=categories, profile=profile, cover=cover,
                               menu_item_count=sum(len(category["items"]) for category in categories))
    products = db.execute(
        "SELECT * FROM products WHERE merchant_id = ? ORDER BY monetary_value", (merchant_id,)
    ).fetchall()
    return render_template("store.html", merchant=merchant, products=products,
                           menu_categories=[], menu_item_count=0, profile=profile,
                           cover=merchant["image_url"],
                           price_notice=(SWEET_CRUMBS_PRICE_NOTICE
                                         if merchant["name"] == "Sweet Crumbs Bakery" else None))


def parse_budget(query, supplied_budget=None):
    """Return an explicit or query-detected UGX ceiling, or None."""
    if supplied_budget not in (None, ""):
        raw = str(supplied_budget).strip().replace(",", "")
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError("Budget must be a whole number of UGX.") from exc
        if value < 0:
            raise ValueError("Budget cannot be negative.")
        return value

    amount = r"(\d[\d,]*(?:\.\d+)?\s*[km]?)"
    match = re.search(
        rf"\b(?:under|below|less than|budget(?: of)?|up to|max(?:imum)?|<=)\s*"
        rf"(?:ugx\s*)?{amount}",
        query,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(rf"\bugx\s*{amount}", query, re.IGNORECASE)
    if not match:
        match = re.search(r"\b\d[\d,]*(?:\.\d+)?\s*[km]\b", query, re.IGNORECASE)
    if not match:
        return None

    raw = match.group(1) if match.lastindex else match.group(0)
    raw = raw.strip().lower().replace(",", "")
    multiplier = 1
    if raw.endswith("k"):
        multiplier, raw = 1_000, raw[:-1].strip()
    elif raw.endswith("m"):
        multiplier, raw = 1_000_000, raw[:-1].strip()
    return int(float(raw) * multiplier)


def _tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


RETIRED_PRODUCTS = {(m["name"], title) for m in MERCHANTS for title in m.get("retired_products", ())}
RECOMMENDER_MODE = os.environ.get("ML_RECOMMENDER", "hybrid")  # tfidf|lsa|embed|hybrid|builtin


def gift_catalogue(db):
    """Everything a customer can currently buy, from every merchant.

    A merchant sells either menu items (e.g. KFC) or fixed gift products (e.g. Sweet
    Crumbs Bakery). Products of a merchant that has an active menu, and products a
    seed has retired but kept only for old vouchers, are not offered.
    """
    rows = [dict(row, kind="menu_item") for row in db.execute("""
        SELECT mi.id, mi.merchant_id, m.name AS merchant_name, m.category AS merchant_category,
               mi.category, mi.name, mi.variant, mi.description, mi.price_ugx, mi.tags,
               mi.image_filename
        FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
        WHERE mi.is_active=1 ORDER BY mi.id
    """)]
    for row in db.execute("""
        SELECT p.id, p.merchant_id, m.name AS merchant_name, m.category AS merchant_category,
               m.category AS category, p.title AS name, NULL AS variant, p.description,
               p.monetary_value AS price_ugx, '' AS tags, p.image_url
        FROM products p JOIN merchants m ON m.id=p.merchant_id
        WHERE NOT EXISTS (SELECT 1 FROM menu_items mi
                          WHERE mi.merchant_id=p.merchant_id AND mi.is_active=1)
        ORDER BY p.id
    """):
        if (row["merchant_name"], row["name"]) not in RETIRED_PRODUCTS:
            rows.append(dict(row, kind="product"))
    return rows


def _builtin_rank(rows, query, budget=None, limit=10):
    """Dependency-free TF-IDF ranking, used when scikit-learn is not installed."""
    query_terms = _tokens(query)
    if not query_terms or not rows:
        return []

    documents = [
        _tokens(" ".join((row["name"], row["variant"] or "", row["description"] or "",
                          row["tags"] or "", row["category"], row["merchant_name"],
                          row["merchant_category"])))
        for row in rows
    ]
    document_frequencies = defaultdict(int)
    for terms in documents:
        for term in set(terms):
            document_frequencies[term] += 1
    document_count = len(documents)
    inverse_frequency = {
        term: math.log((document_count + 1) / (frequency + 1)) + 1
        for term, frequency in document_frequencies.items()
    }

    def vector(terms):
        counts = defaultdict(int)
        for term in terms:
            counts[term] += 1
        length = len(terms) or 1
        return {
            term: (count / length) * inverse_frequency.get(term, 0)
            for term, count in counts.items()
        }

    query_vector = vector(query_terms)
    query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
    ranked = []
    for index, (row, terms) in enumerate(zip(rows, documents)):
        item_vector = vector(terms)
        item_norm = math.sqrt(sum(weight * weight for weight in item_vector.values()))
        dot = sum(weight * item_vector.get(term, 0) for term, weight in query_vector.items())
        similarity = dot / (query_norm * item_norm) if query_norm and item_norm else 0
        if similarity > 0:
            ranked.append((similarity, index, row))
    ranked.sort(key=lambda result: (-result[0], result[1]))
    if budget is not None:
        ranked = [result for result in ranked if result[2]["price_ugx"] <= budget]
    return [(row, score) for score, _index, row in ranked[:limit]]


def _ml_rank(rows, query, budget=None, limit=10, mode="hybrid"):
    """Rank with the ml package (scikit-learn); None when it is not installed."""
    try:
        from ml.service import rank
    except ImportError:
        return None
    by_key = {(row["kind"], row["id"]): row for row in rows}
    results = rank(query, rows=rows, budget=budget, k=limit, mode=mode)
    return [(by_key[(item["kind"], item["id"])], item["score"])
            for item in results if item["score"] > 0]


def recommend_gifts(db, query, budget=None, limit=10, mode=None):
    """Rank gifts from every merchant for a free-text request under a UGX ceiling."""
    mode = mode or RECOMMENDER_MODE
    rows = gift_catalogue(db)
    if not query.strip() or not rows:
        return []
    ranked = _ml_rank(rows, query, budget, limit, mode) if mode != "builtin" else None
    if ranked is None:
        ranked = _builtin_rank(rows, query, budget, limit)

    results = []
    for row, score in ranked:
        if row["kind"] == "menu_item":
            image = menu_item_image(row["image_filename"])
            buy_url = url_for("buy_menu_item", menu_item_id=row["id"])
        else:
            image = row["image_url"]
            buy_url = url_for("buy_gift", product_id=row["id"])
        results.append({
            "kind": row["kind"],
            "item": {
                "id": row["id"],
                "name": row["name"],
                "variant": row["variant"],
                "description": row["description"],
                "category": row["category"],
            },
            "merchant": {"id": row["merchant_id"], "name": row["merchant_name"]},
            "price": row["price_ugx"],
            "image": image,
            "buy_url": buy_url,
            "similarity": score,
        })
    return results


# Older name kept for callers written when KFC was the only menu merchant.
recommend_menu_items = recommend_gifts


def _read_markdown_table(path):
    """Rows of the first markdown table in a results file, plus the other text lines."""
    rows, notes, header = [], [], None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], []
    for line in lines:
        line = line.strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if header is None:
                header = cells
            else:
                rows.append(dict(zip(header, cells)))
        elif line:
            notes.append(line.lstrip("- "))
    return rows, notes


@app.route("/ai")
def how_ai_works():
    """Explains the two ML components and shows their offline evaluation results."""
    ml_dir = BASE_DIR / "ml"
    rec_rows, rec_notes = _read_markdown_table(ml_dir / "eval" / "results.md")
    fraud_rows, fraud_notes = _read_markdown_table(ml_dir / "fraud" / "results.md")
    for row in rec_rows:
        try:
            row["ndcg"] = float(row.get("NDCG@5", "0"))
        except ValueError:
            row["ndcg"] = 0.0
    best = max(rec_rows, key=lambda r: r["ndcg"], default=None)

    status = ml_status().removeprefix("[ml] ")
    recommender_status, _, fraud_status = status.partition("; fraud check: ")
    recommender_status = recommender_status.removeprefix("recommender mode: ")

    if recommender_status.startswith("builtin"):
        running_model = None
    elif recommender_status.startswith("hybrid"):
        running_model = "hybrid tfidf+lsa" if "LSA used" in recommender_status else "hybrid tfidf+embeddings"
    else:
        running_model = {"tfidf": "tfidf (baseline)", "lsa": "lsa", "embed": "embeddings"}.get(
            recommender_status.split(" ")[0])

    db = get_db()
    live = db.execute("""
        SELECT COUNT(*) AS checked, COALESCE(SUM(risk_flag), 0) AS flagged
        FROM audit_log WHERE risk_flag IS NOT NULL
    """).fetchone()
    try:
        query_count = sum(1 for _ in (ml_dir / "eval" / "gift_queries.csv").open(encoding="utf-8")) - 1
    except OSError:
        query_count = None
    return render_template(
        "ai.html", rec_rows=rec_rows, rec_notes=rec_notes, best=best,
        fraud_rows=fraud_rows, fraud_notes=fraud_notes, running_model=running_model,
        recommender_status=recommender_status, fraud_status=fraud_status,
        live=live, catalogue_size=len(gift_catalogue(db)), query_count=query_count,
        has_confusion=(ml_dir / "fraud" / "confusion.png").is_file(),
    )


@app.route("/ai/confusion.png")
def fraud_confusion_image():
    path = BASE_DIR / "ml" / "fraud" / "confusion.png"
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/credits")
def photo_credits():
    """Photographer credits for stock photos downloaded by fetch_images.py."""
    import json

    credits_file = BASE_DIR / "static" / "img" / "credits.json"
    try:
        credits = json.loads(credits_file.read_text()) if credits_file.is_file() else {}
    except ValueError:
        credits = {}
    rows = sorted(
        ({"file": path, **info} for path, info in credits.items()
         if menu_item_image(path)),
        key=lambda row: (row.get("store", ""), row["file"]),
    )
    return render_template("credits.html", credits=rows)


@app.route("/recommend")
def recommend():
    query = request.args.get("q", "").strip()
    try:
        budget = parse_budget(query, request.args.get("budget"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "recommendations": recommend_gifts(get_db(), query, budget),
        "budget": budget,
    })


def _validate_gift_form(form):
    errors, clean = {}, {}

    sender = re.sub(r"\s+", " ", form.get("sender_name", "")).strip()
    if not 2 <= len(sender) <= 60:
        errors["sender_name"] = "Enter your name (2 to 60 characters)."
    clean["sender_name"] = sender

    raw_phone = form.get("recipient_phone", "").strip()
    phone = normalise_phone(raw_phone)
    if not phone:
        errors["recipient_phone"] = "Enter a valid Ugandan mobile number, e.g. 0770 123 456."
    clean["recipient_phone"] = phone or raw_phone

    message = form.get("message", "").strip()
    if len(message) > MAX_MESSAGE_LEN:
        errors["message"] = f"Keep your message under {MAX_MESSAGE_LEN} characters."
    clean["message"] = message

    method = form.get("payment_method", "")
    if method not in PAYMENT_METHODS:
        errors["payment_method"] = "Choose how you want to pay."
    clean["payment_method"] = method
    return clean, errors


@app.route("/buy/<int:product_id>", methods=["GET", "POST"])
def buy_gift(product_id):
    return _buy(product_id=product_id)


@app.route("/buy/menu/<int:menu_item_id>", methods=["GET", "POST"])
def buy_menu_item(menu_item_id):
    return _buy(menu_item_id=menu_item_id)


def _buy(product_id=None, menu_item_id=None):
    db = get_db()
    if menu_item_id is not None:
        product = db.execute("""
            SELECT mi.id, mi.merchant_id, mi.name AS title, mi.variant, mi.description,
                   mi.price_ugx AS monetary_value, m.name AS merchant_name,
                   m.icon, m.accent, mi.id AS menu_item_id
            FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
            WHERE mi.id=? AND mi.is_active=1
        """, (menu_item_id,)).fetchone()
    else:
        product = db.execute("""
            SELECT p.*, m.name AS merchant_name, m.icon AS icon, m.accent AS accent,
                   NULL AS variant, NULL AS menu_item_id
            FROM products p JOIN merchants m ON p.merchant_id = m.id WHERE p.id = ?
        """, (product_id,)).fetchone()
    if not product:
        abort(404)

    form, errors = {"payment_method": "mtn"}, {}
    if request.method == "POST":
        form, errors = _validate_gift_form(request.form)
        if not errors:
            if menu_item_id is not None:
                db.execute("BEGIN IMMEDIATE")
                product = db.execute("""
                    SELECT mi.id, mi.merchant_id, mi.name AS title, mi.variant, mi.description,
                           mi.price_ugx AS monetary_value, m.name AS merchant_name,
                           m.icon, m.accent, mi.id AS menu_item_id
                    FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
                    WHERE mi.id=? AND mi.is_active=1
                """, (menu_item_id,)).fetchone()
                if not product:
                    db.rollback()
                    abort(404)
            for attempt in range(5):  # retry on the (very unlikely) code collision
                if menu_item_id is not None and attempt:
                    db.execute("BEGIN IMMEDIATE")
                    product = db.execute("""
                        SELECT mi.id, mi.merchant_id, mi.name AS title, mi.variant, mi.description,
                               mi.price_ugx AS monetary_value, m.name AS merchant_name,
                               m.icon, m.accent, mi.id AS menu_item_id
                        FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
                        WHERE mi.id=? AND mi.is_active=1
                    """, (menu_item_id,)).fetchone()
                    if not product:
                        db.rollback()
                        abort(404)
                code = generate_voucher_code()
                try:
                    if menu_item_id is not None:
                        db.execute(
                            """INSERT INTO vouchers (
                                   voucher_code, merchant_id, product_id, menu_item_id,
                                   price_at_purchase, sender_name, recipient_phone, message,
                                   monetary_value, payment_method, created_at
                               ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (code, product["merchant_id"], product["menu_item_id"],
                             product["monetary_value"], form["sender_name"],
                             form["recipient_phone"], form["message"],
                             product["monetary_value"], form["payment_method"], utc_now()),
                        )
                    else:
                        db.execute(
                            """INSERT INTO vouchers (voucher_code, merchant_id, product_id,
                                   price_at_purchase, sender_name, recipient_phone, message,
                                   monetary_value, payment_method, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (code, product["merchant_id"], product["id"],
                             product["monetary_value"], form["sender_name"],
                             form["recipient_phone"], form["message"],
                             product["monetary_value"], form["payment_method"], utc_now()),
                        )
                    db.commit()
                    break
                except sqlite3.IntegrityError:
                    db.rollback()
            else:
                abort(500)
            session["just_purchased"] = code
            flash("Payment received. Your gift voucher is ready to send.", "success")
            return redirect(url_for("view_voucher", voucher_code=code))
        flash("Please fix the highlighted fields and try again.", "danger")

    status = 400 if errors else 200
    return render_template("buy.html", product=product, form=form, errors=errors,
                           payment_methods=PAYMENT_METHODS, max_message=MAX_MESSAGE_LEN,
                           price_notice=(SWEET_CRUMBS_PRICE_NOTICE
                                         if product["merchant_name"] == "Sweet Crumbs Bakery" else None)), status


def fetch_voucher(db, code):
    return db.execute("""
        SELECT v.*, m.name AS merchant_name, m.icon AS icon, m.accent AS accent,
               COALESCE(mi.name, p.title) AS product_title,
               COALESCE(mi.description, p.description) AS product_desc,
               mi.variant AS menu_item_variant, mi.id AS menu_item_id
        FROM vouchers v
        JOIN merchants m ON v.merchant_id = m.id
        LEFT JOIN products p ON v.product_id = p.id
        LEFT JOIN menu_items mi ON v.menu_item_id = mi.id
        WHERE v.voucher_code = ?
    """, (code,)).fetchone()


def build_share(voucher, link):
    """Prepare WhatsApp / SMS deep links and the message text for the share modal."""
    price_note = (
        " Proposed demo price pending bakery confirmation."
        if voucher["merchant_name"] == "Sweet Crumbs Bakery" else ""
    )
    text = (f"{voucher['sender_name']} sent you a gift on Smart Gifting: {voucher['product_title']} "
            f"at {voucher['merchant_name']} ({ugx_filter(voucher['monetary_value'])}).{price_note} "
            f"Open your voucher: {link}  Code: {voucher['voucher_code']}")
    phone = normalise_phone(voucher["recipient_phone"]) or voucher["recipient_phone"]
    digits = re.sub(r"\D", "", phone)
    return {
        "text": text,
        "link": link,
        "whatsapp": f"https://wa.me/{digits}?text={quote(text)}",
        "sms": f"sms:{phone}?&body={quote(text)}",
        "phone": phone,
    }


@app.route("/voucher/<voucher_code>")
def view_voucher(voucher_code):
    db = get_db()
    code = normalise_code(voucher_code)
    voucher = fetch_voucher(db, code)
    if not voucher:
        abort(404)
    # The share modal opens once, right after purchase, not on every refresh.
    show_share = session.get("just_purchased") == code
    if show_share:
        session.pop("just_purchased", None)
    link = url_for("view_voucher", voucher_code=code, _external=True)
    return render_template("voucher.html", voucher=voucher, share=build_share(voucher, link),
                           show_share=show_share,
                           price_notice=(SWEET_CRUMBS_PRICE_NOTICE
                                         if voucher["merchant_name"] == "Sweet Crumbs Bakery" else None))


# --------------------------------------------------------------------------
# Cashier portal (store sign-in, verification, redemption, audit trail)
# --------------------------------------------------------------------------
def client_rate_limit_key():
    """Return a keyed digest of the client IP without retaining the raw address."""
    address = request.remote_addr or "unknown"
    secret = app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, address.encode("utf-8"), hashlib.sha256).hexdigest()


def log_event(db, code, merchant_id, outcome, client_key=None, menu_item_id=None, cashier=None,
              risk=None):
    db.execute(
        "INSERT INTO audit_log (voucher_code, merchant_id, outcome, created_at, client_key, "
        "menu_item_id, cashier, risk_score, risk_flag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (code[:24], merchant_id, outcome, utc_now(), client_key, menu_item_id, cashier,
         risk["score"] if risk else None,
         int(risk["suspicious"]) if risk else None),
    )
    db.commit()


# --------------------------------------------------------------------------
# Fraud check (advisory): flags unusual redemptions for the cashier, never blocks.
# The model is trained on SYNTHETIC data, so a flag asks the cashier to double-check
# the recipient rather than refusing a customer.
# --------------------------------------------------------------------------
FRAUD_CHECK = os.environ.get("FRAUD_CHECK", "1") != "0"
_fraud_scorer = None  # None = not loaded yet, False = model unavailable


def fraud_scorer():
    """Load the Isolation Forest once; None when scikit-learn or the model is missing."""
    global _fraud_scorer
    if _fraud_scorer is None:
        try:
            from ml.fraud.detect import FraudScorer
            _fraud_scorer = FraudScorer()
        except Exception as exc:  # ImportError, missing file, incompatible pickle
            app.logger.warning("Fraud model unavailable (%s); using fixed rules.", exc)
            _fraud_scorer = False
    return _fraud_scorer or None


def merchant_typical_amount(db, merchant_id):
    """Median price of what this merchant currently sells (None if nothing is listed)."""
    prices = sorted(row["price_ugx"] for row in gift_catalogue(db)
                    if row["merchant_id"] == merchant_id and row["price_ugx"] > 0)
    if not prices:
        return None
    middle = len(prices) // 2
    return prices[middle] if len(prices) % 2 else (prices[middle - 1] + prices[middle]) / 2


def redemption_features(db, voucher, merchant_id, client_key):
    """The six model features for redeeming `voucher` now, at this merchant's till."""
    now = datetime.now(timezone.utc)
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        created = datetime.strptime(voucher["created_at"], fmt).replace(tzinfo=timezone.utc)
        hours_since_purchase = max((now - created).total_seconds() / 3600, 0.0)
    except (TypeError, ValueError):
        created, hours_since_purchase = now, 24.0  # legacy row without a usable timestamp
    hour_ago = (now - timedelta(hours=1)).strftime(fmt)
    # "Device" = the recipient's phone: many codes funnelled to one phone in an hour,
    # at any store. (The cashier's till is not used: a busy till redeems a lot.)
    recipient_redemptions = db.execute(
        "SELECT COUNT(*) FROM audit_log a JOIN vouchers v ON v.voucher_code = a.voucher_code "
        "WHERE a.outcome = 'REDEEMED' AND v.recipient_phone = ? AND a.created_at >= ?",
        (voucher["recipient_phone"], hour_ago)).fetchone()[0]
    # Buyer = sender name (there are no buyer accounts), across every merchant.
    buyer_vouchers = db.execute(
        "SELECT COUNT(*) FROM vouchers WHERE LOWER(sender_name) = LOWER(?) "
        "AND created_at > ? AND created_at <= ?",
        (voucher["sender_name"], (created - timedelta(hours=24)).strftime(fmt),
         created.strftime(fmt))).fetchone()[0]
    failed_attempts = db.execute(
        "SELECT COUNT(*) FROM audit_log WHERE merchant_id = ? AND client_key = ? "
        "AND outcome IN ('NOT_FOUND', 'WRONG_STORE') AND created_at >= ?",
        (merchant_id, client_key,
         (now - timedelta(minutes=LOOKUP_WINDOW_MINUTES)).strftime(fmt))).fetchone()[0]
    return {
        "hours_since_purchase": hours_since_purchase,
        "device_redemptions_1h": recipient_redemptions,
        "buyer_vouchers_24h": max(buyer_vouchers, 1),
        "failed_code_attempts": failed_attempts,
        "redeem_hour": now.astimezone(EAT).hour,
        "amount_ugx": voucher["price_at_purchase"] or voucher["monetary_value"],
    }


def assess_redemption(db, voucher, merchant_id, client_key):
    """Fraud assessment for any merchant: {suspicious, score, reasons, method} or None."""
    if not FRAUD_CHECK:
        return None
    event = redemption_features(db, voucher, merchant_id, client_key)
    scorer = fraud_scorer()
    if scorer is not None:
        try:
            return scorer.assess(event, merchant_typical_amount(db, merchant_id))
        except Exception as exc:
            app.logger.warning("Fraud model failed (%s); using fixed rules.", exc)
    from ml.fraud.rules import rule_reasons, rule_suspicious
    return {"suspicious": rule_suspicious(event), "score": None,
            "reasons": rule_reasons(event), "method": "rules"}


def evaluate_voucher(db, cashier, code, log, client_key=None):
    """Classify a code for this cashier's store; optionally write the audit entry."""
    voucher = fetch_voucher(db, code)
    if voucher is None:
        state, outcome = "not_found", "NOT_FOUND"
    elif voucher["merchant_id"] != cashier["merchant_id"]:
        state, outcome = "wrong_store", "WRONG_STORE"
    elif voucher["status"] != "ACTIVE":
        state, outcome = "used", "ALREADY_USED"
    else:
        state, outcome = "active", None
    if log and outcome:
        log_event(db, code, cashier["merchant_id"], outcome, client_key)
    shown = voucher if state in ("active", "used") else None  # never leak other stores' vouchers
    return {"state": state, "code": code, "voucher": shown,
            "other_store": voucher["merchant_name"] if state == "wrong_store" else None}


def too_many_failures(db, merchant_id, client_key):
    since = (datetime.now(timezone.utc) - timedelta(minutes=LOOKUP_WINDOW_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    count = db.execute(
        "SELECT COUNT(*) FROM audit_log WHERE merchant_id = ? AND outcome IN ('NOT_FOUND', 'WRONG_STORE') "
        "AND client_key = ? AND created_at >= ?",
        (merchant_id, client_key, since),
    ).fetchone()[0]
    return count >= MAX_FAILED_LOOKUPS


def authenticated_cashier(db):
    """Resolve the signed-in cashier's store from the database, not session claims."""
    stored = session.get("cashier")
    if not isinstance(stored, dict):
        return None
    try:
        merchant_id = int(stored.get("merchant_id"))
    except (TypeError, ValueError):
        session.pop("cashier", None)
        return None
    merchant = db.execute(
        "SELECT id, name FROM merchants WHERE id = ?", (merchant_id,)
    ).fetchone()
    if merchant is None:
        session.pop("cashier", None)
        return None
    cashier = {"merchant_id": merchant["id"], "name": merchant["name"]}
    if stored != cashier:
        session["cashier"] = cashier
    return cashier


def cashier_stats(db, merchant_id):
    start_of_day = datetime.now(EAT).replace(hour=0, minute=0, second=0, microsecond=0)
    since = start_of_day.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    redeemed = db.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(monetary_value), 0) AS value FROM vouchers "
        "WHERE merchant_id = ? AND status = 'USED' AND redeemed_at >= ?", (merchant_id, since)).fetchone()
    rejected = db.execute(
        "SELECT COUNT(*) FROM audit_log WHERE merchant_id = ? AND outcome != 'REDEEMED' AND created_at >= ?",
        (merchant_id, since)).fetchone()[0]
    outstanding = db.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(monetary_value), 0) AS value FROM vouchers "
        "WHERE merchant_id = ? AND status = 'ACTIVE'", (merchant_id,)).fetchone()
    return {"redeemed_n": redeemed["n"], "redeemed_value": redeemed["value"],
            "rejected": rejected, "outstanding_n": outstanding["n"], "outstanding_value": outstanding["value"]}


def audit_trail(db, merchant_id, limit=15):
    return db.execute("""
        SELECT a.*, COALESCE(v.price_at_purchase, v.monetary_value) AS monetary_value,
               v.sender_name, COALESCE(mi.name, p.title) AS product_title,
               mi.variant AS menu_item_variant
        FROM audit_log a
        LEFT JOIN vouchers v ON v.voucher_code = a.voucher_code AND v.merchant_id = a.merchant_id
        LEFT JOIN products p ON p.id = v.product_id
        LEFT JOIN menu_items mi ON mi.id = COALESCE(a.menu_item_id, v.menu_item_id)
        WHERE a.merchant_id = ? ORDER BY a.id DESC LIMIT ?
    """, (merchant_id, limit)).fetchall()


@app.route("/merchant/verify")
def merchant_verify():
    db = get_db()
    cashier = authenticated_cashier(db)
    if not cashier:
        stores = db.execute("SELECT id, name, category FROM merchants ORDER BY name").fetchall()
        return render_template("verify.html", stores=stores, prefill=request.args.get("prefill", ""))

    code = normalise_code(request.args.get("code", "")) if request.args.get("code") else None
    result = evaluate_voucher(db, cashier, code, log=False) if code else None
    if result and result["state"] == "active":
        result["risk"] = assess_redemption(db, result["voucher"], cashier["merchant_id"],
                                           client_rate_limit_key())
    return render_template("verify.html", result=result,
                           prefill=request.args.get("prefill", ""),
                           stats=cashier_stats(db, cashier["merchant_id"]),
                           trail=audit_trail(db, cashier["merchant_id"]),
                           price_notice=(SWEET_CRUMBS_PRICE_NOTICE
                                         if cashier["name"] == "Sweet Crumbs Bakery" else None))


@app.route("/merchant/login", methods=["POST"])
def merchant_login():
    db = get_db()
    try:
        merchant_id = int(request.form.get("merchant_id", ""))
    except ValueError:
        merchant_id = 0
    merchant = db.execute("SELECT id, name FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
    pin = request.form.get("pin", "")
    pin_ok = secrets.compare_digest(pin.encode(), app.config["CASHIER_PIN"].encode())
    if not merchant or not pin_ok:
        flash("Store or PIN is incorrect. Check both and try again.", "danger")
        return redirect(url_for("merchant_verify", prefill=request.form.get("prefill", "")))
    session["cashier"] = {"merchant_id": merchant["id"], "name": merchant["name"]}
    flash(f"Signed in to {merchant['name']}.", "success")
    return redirect(url_for("merchant_verify", prefill=request.form.get("prefill", "")))


@app.route("/merchant/logout", methods=["POST"])
def merchant_logout():
    session.pop("cashier", None)
    flash("Signed out of the cashier portal.", "info")
    return redirect(url_for("merchant_verify"))


@app.route("/merchant/lookup", methods=["POST"])
def merchant_lookup():
    db = get_db()
    cashier = authenticated_cashier(db)
    if not cashier:
        return redirect(url_for("merchant_verify"))
    code = normalise_code(request.form.get("voucher_code", ""))
    if not code:
        flash("Enter a voucher code first.", "warning")
        return redirect(url_for("merchant_verify"))
    client_key = client_rate_limit_key()
    if too_many_failures(db, cashier["merchant_id"], client_key):
        flash(f"Too many invalid codes. Wait {LOOKUP_WINDOW_MINUTES} minutes before trying again.", "danger")
        return redirect(url_for("merchant_verify"))
    evaluate_voucher(db, cashier, code, log=True, client_key=client_key)
    return redirect(url_for("merchant_verify", code=code))


@app.route("/merchant/redeem", methods=["POST"])
def merchant_redeem():
    db = get_db()
    cashier = authenticated_cashier(db)
    if not cashier:
        return redirect(url_for("merchant_verify"))
    code = normalise_code(request.form.get("voucher_code", ""))
    if not code:
        flash("Enter a voucher code first.", "warning")
        return redirect(url_for("merchant_verify"))
    client_key = client_rate_limit_key()
    if too_many_failures(db, cashier["merchant_id"], client_key):
        flash(f"Too many invalid codes. Wait {LOOKUP_WINDOW_MINUTES} minutes before trying again.", "danger")
        return redirect(url_for("merchant_verify"))
    result = evaluate_voucher(db, cashier, code, log=True, client_key=client_key)
    if result["state"] == "active":
        # Scored before the status flips, so this redemption does not count itself.
        risk = assess_redemption(db, result["voucher"], cashier["merchant_id"], client_key)
        # Atomic compare-and-set: only one request can flip ACTIVE -> USED.
        cur = db.execute(
            "UPDATE vouchers SET status = 'USED', redeemed_at = ? "
            "WHERE voucher_code = ? AND status = 'ACTIVE' AND merchant_id = ?",
            (utc_now(), code, cashier["merchant_id"]))
        db.commit()
        if cur.rowcount == 1:
            voucher = result["voucher"]
            log_event(
                db, code, cashier["merchant_id"], "REDEEMED", client_key=client_key,
                menu_item_id=voucher["menu_item_id"], cashier=cashier["name"], risk=risk,
            )
            flash(f"{code} redeemed. Hand over the gift.", "success")
            if risk and risk["suspicious"]:
                flash("Fraud check flagged this redemption"
                      + (f" ({'; '.join(risk['reasons'])})" if risk["reasons"] else "")
                      + ". It has been recorded for review.", "warning")
        else:
            log_event(db, code, cashier["merchant_id"], "ALREADY_USED")
            flash("Another cashier just redeemed this voucher. Do not hand over the gift.", "warning")
    elif result["state"] == "used":
        flash("This voucher was already redeemed. Do not hand over the gift.", "warning")
    elif result["state"] == "wrong_store":
        flash(f"This voucher belongs to {result['other_store']}, not your store.", "danger")
    else:
        flash("Voucher code not found.", "danger")
    return redirect(url_for("merchant_verify", code=code))


# --------------------------------------------------------------------------
def ml_status():
    """One line saying which ML pieces are really active (printed at startup)."""
    from importlib.util import find_spec
    mode = RECOMMENDER_MODE
    if find_spec("sklearn") is None:
        recommender = "builtin TF-IDF (scikit-learn not installed)"
    elif mode in ("embed", "hybrid") and find_spec("sentence_transformers") is None:
        recommender = f"{mode} (sentence-transformers not installed, LSA used as the semantic model)"
    else:
        recommender = mode
    if not FRAUD_CHECK:
        fraud = "off (FRAUD_CHECK=0)"
    elif fraud_scorer() is not None:
        fraud = "Isolation Forest model loaded"
    else:
        fraud = "model NOT loaded, using fixed rules"
    return f"[ml] recommender mode: {recommender}; fraud check: {fraud}"


bootstrap()
print(ml_status(), flush=True)

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
