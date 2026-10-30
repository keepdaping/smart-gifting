"""Smart Digital Gifting App - Flask application.

A closed-loop digital voucher marketplace. A sender buys a gift package from a
partner store, the recipient receives a unique code (via SMS / WhatsApp), and a
cashier at that store verifies and redeems the code exactly once.

Architecture
------------
* ``catalogue.py``  - partner stores and gift packages (seed data).
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
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from markupsafe import Markup, escape
from werkzeug.middleware.proxy_fix import ProxyFix

from catalogue import MERCHANTS, image_url

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
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_code TEXT UNIQUE NOT NULL,
            merchant_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            recipient_phone TEXT NOT NULL,
            message TEXT,
            monetary_value INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'USED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_code TEXT NOT NULL,
            merchant_id INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            client_key TEXT,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        );
    """)
    # Columns added after the first prototype (older gifting.db files get upgraded).
    _add_missing_columns(cur, "merchants", {"image_url": "TEXT", "icon": "TEXT", "accent": "TEXT"})
    _add_missing_columns(cur, "products", {"image_url": "TEXT"})
    _add_missing_columns(cur, "vouchers", {"payment_method": "TEXT", "redeemed_at": "TIMESTAMP"})
    _add_missing_columns(cur, "audit_log", {"client_key": "TEXT"})

    cur.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_merchant ON vouchers (merchant_id, status)")
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


def seed_db(path=None):
    """Insert or refresh every partner store and package (idempotent, no duplicates)."""
    conn = connect(path)
    cur = conn.cursor()
    try:
        for m in MERCHANTS:
            row = cur.execute("SELECT id FROM merchants WHERE name = ?", (m["name"],)).fetchone()
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
        conn.commit()
    finally:
        conn.close()


def bootstrap(path=None):
    """Prepare the database. Runs at import so it also works under gunicorn."""
    init_db(path)
    seed_db(path)


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
        SELECT m.*, COUNT(p.id) AS product_count, MIN(p.monetary_value) AS min_price,
               MAX(p.monetary_value) AS max_price, GROUP_CONCAT(p.title, '|') AS product_titles
        FROM merchants m LEFT JOIN products p ON p.merchant_id = m.id
        GROUP BY m.id ORDER BY m.id
    """).fetchall()
    categories = {}
    for m in merchants:
        categories[m["category"]] = categories.get(m["category"], 0) + 1
    return render_template("index.html", merchants=merchants, categories=list(categories.items()))


@app.route("/store/<int:merchant_id>")
def store_catalog(merchant_id):
    db = get_db()
    merchant = db.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
    if not merchant:
        abort(404)
    products = db.execute(
        "SELECT * FROM products WHERE merchant_id = ? ORDER BY monetary_value", (merchant_id,)
    ).fetchall()
    return render_template("store.html", merchant=merchant, products=products)


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
    db = get_db()
    product = db.execute("""
        SELECT p.*, m.name AS merchant_name, m.icon AS icon, m.accent AS accent
        FROM products p JOIN merchants m ON p.merchant_id = m.id WHERE p.id = ?
    """, (product_id,)).fetchone()
    if not product:
        abort(404)

    form, errors = {"payment_method": "mtn"}, {}
    if request.method == "POST":
        form, errors = _validate_gift_form(request.form)
        if not errors:
            for _ in range(5):  # retry on the (very unlikely) code collision
                code = generate_voucher_code()
                try:
                    db.execute(
                        """INSERT INTO vouchers (voucher_code, merchant_id, product_id, sender_name,
                               recipient_phone, message, monetary_value, payment_method, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (code, product["merchant_id"], product["id"], form["sender_name"],
                         form["recipient_phone"], form["message"], product["monetary_value"],
                         form["payment_method"], utc_now()),
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
                           payment_methods=PAYMENT_METHODS, max_message=MAX_MESSAGE_LEN), status


def fetch_voucher(db, code):
    return db.execute("""
        SELECT v.*, m.name AS merchant_name, m.icon AS icon, m.accent AS accent,
               p.title AS product_title, p.description AS product_desc
        FROM vouchers v
        JOIN merchants m ON v.merchant_id = m.id
        JOIN products p ON v.product_id = p.id
        WHERE v.voucher_code = ?
    """, (code,)).fetchone()


def build_share(voucher, link):
    """Prepare WhatsApp / SMS deep links and the message text for the share modal."""
    text = (f"{voucher['sender_name']} sent you a gift on Smart Gifting: {voucher['product_title']} "
            f"at {voucher['merchant_name']} ({ugx_filter(voucher['monetary_value'])}). "
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
                           show_share=show_share)


# --------------------------------------------------------------------------
# Cashier portal (store sign-in, verification, redemption, audit trail)
# --------------------------------------------------------------------------
def client_rate_limit_key():
    """Return a keyed digest of the client IP without retaining the raw address."""
    address = request.remote_addr or "unknown"
    secret = app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, address.encode("utf-8"), hashlib.sha256).hexdigest()


def log_event(db, code, merchant_id, outcome, client_key=None):
    db.execute(
        "INSERT INTO audit_log (voucher_code, merchant_id, outcome, created_at, client_key) "
        "VALUES (?, ?, ?, ?, ?)",
        (code[:24], merchant_id, outcome, utc_now(), client_key),
    )
    db.commit()


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
        SELECT a.*, v.monetary_value, v.sender_name, p.title AS product_title
        FROM audit_log a
        LEFT JOIN vouchers v ON v.voucher_code = a.voucher_code AND v.merchant_id = a.merchant_id
        LEFT JOIN products p ON p.id = v.product_id
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
    return render_template("verify.html", result=result,
                           prefill=request.args.get("prefill", ""),
                           stats=cashier_stats(db, cashier["merchant_id"]),
                           trail=audit_trail(db, cashier["merchant_id"]))


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
        # Atomic compare-and-set: only one request can flip ACTIVE -> USED.
        cur = db.execute(
            "UPDATE vouchers SET status = 'USED', redeemed_at = ? "
            "WHERE voucher_code = ? AND status = 'ACTIVE' AND merchant_id = ?",
            (utc_now(), code, cashier["merchant_id"]))
        db.commit()
        if cur.rowcount == 1:
            log_event(db, code, cashier["merchant_id"], "REDEEMED")
            flash(f"{code} redeemed. Hand over the gift.", "success")
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
bootstrap()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
