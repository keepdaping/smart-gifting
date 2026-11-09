"""Idempotently load every non-KFC store menu (store_menus.py) into menu_items.

Uses the same upsert rules as seed_kfc.py: rows not in the current menu are
deactivated (never deleted, so old vouchers keep their item), prices that
change get a fresh price_updated_at.
"""

import os
import sqlite3
from pathlib import Path

from store_menus import STORE_MENUS

BASE_DIR = Path(__file__).resolve().parent


def _connect(path=None):
    conn = sqlite3.connect(
        path or os.environ.get("GIFT_DB_PATH", str(BASE_DIR / "gifting.db")),
        timeout=15,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def seed_store_menu(cur, merchant_id, slug, items):
    cur.execute("UPDATE menu_items SET is_active=0 WHERE merchant_id=?", (merchant_id,))
    for section, name, variant, description, price, tags, image in items:
        image_filename = f"{slug}/{image}.jpg" if image else None
        row = cur.execute(
            "SELECT id FROM menu_items WHERE merchant_id=? AND name=? AND variant IS ?",
            (merchant_id, name, variant),
        ).fetchone()
        if row:
            cur.execute(
                """UPDATE menu_items
                   SET category=?, description=?, price_updated_at=
                       CASE WHEN price_ugx != ? THEN CURRENT_DATE ELSE price_updated_at END,
                       price_ugx=?, tags=?, image_filename=?, is_active=1
                   WHERE id=?""",
                (section, description, price, price, tags, image_filename, row["id"]),
            )
        else:
            cur.execute(
                """INSERT INTO menu_items
                   (merchant_id, category, name, variant, description, price_ugx,
                    tags, image_filename, is_active, price_updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_DATE)""",
                (merchant_id, section, name, variant, description, price, tags, image_filename),
            )
    return len(items)


def seed_menus(path=None):
    """Load every store in STORE_MENUS. Stores must already exist (seed_db creates them)."""
    conn = _connect(path)
    cur = conn.cursor()
    total = 0
    try:
        for store_name, store in STORE_MENUS.items():
            merchant = cur.execute(
                "SELECT id FROM merchants WHERE name = ?", (store_name,)
            ).fetchone()
            if not merchant:
                continue
            total += seed_store_menu(cur, merchant["id"], store["slug"], store["items"])
        conn.commit()
        return total
    finally:
        conn.close()


if __name__ == "__main__":
    from app import init_db, seed_db

    init_db()
    seed_db()
    print(f"Seeded {seed_menus()} menu variants across {len(STORE_MENUS)} stores.")
