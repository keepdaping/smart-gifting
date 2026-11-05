"""Idempotently load the KFC Uganda menu into the menu_items table."""

import os
import sqlite3
from pathlib import Path

from kfc_menu import KFC_MENU

BASE_DIR = Path(__file__).resolve().parent


def seed_kfc(path=None):
    """Create/update the KFC merchant and upsert its current menu."""
    conn = sqlite3.connect(
        path or os.environ.get("GIFT_DB_PATH", str(BASE_DIR / "gifting.db")),
        timeout=15,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    try:
        merchant = cur.execute(
            "SELECT id FROM merchants WHERE name = ?", ("KFC",)
        ).fetchone()
        if not merchant:
            merchant = cur.execute(
                "SELECT id FROM merchants WHERE name = ?", ("KFC Uganda",)
            ).fetchone()
            if merchant:
                cur.execute(
                    "UPDATE merchants SET name='KFC' WHERE id=?", (merchant["id"],)
                )
        if merchant:
            merchant_id = merchant["id"]
            cur.execute(
                "UPDATE merchants SET category=?, image_url=NULL, description=?, "
                "icon=?, accent=? WHERE id=?",
                ("Food", "KFC Uganda menu favourites, ready to gift and collect in store.",
                 "bi-egg-fried", "#C8102E", merchant_id),
            )
        else:
            cur.execute(
                "INSERT INTO merchants (name, category, description, icon, accent) "
                "VALUES (?, ?, ?, ?, ?)",
                ("KFC", "Food", "KFC Uganda menu favourites, ready to gift and collect in store.",
                 "bi-egg-fried", "#C8102E"),
            )
            merchant_id = cur.lastrowid

        cur.execute(
            "UPDATE menu_items SET is_active=0 WHERE merchant_id=?", (merchant_id,)
        )
        for category, name, variant, description, price, tags, image in KFC_MENU:
            row = cur.execute(
                "SELECT id FROM menu_items WHERE merchant_id=? AND name=? "
                "AND variant IS ?",
                (merchant_id, name, variant),
            ).fetchone()
            image_filename = f"kfc/{image}.jpg"
            if row:
                cur.execute(
                    """UPDATE menu_items
                       SET category=?, description=?, price_updated_at=
                           CASE WHEN price_ugx != ? THEN CURRENT_DATE ELSE price_updated_at END,
                           price_ugx=?, tags=?, image_filename=?, is_active=1
                       WHERE id=?""",
                    (category, description, price, price, tags, image_filename, row["id"]),
                )
            else:
                cur.execute(
                    """INSERT INTO menu_items
                       (merchant_id, category, name, variant, description, price_ugx,
                        tags, image_filename, is_active, price_updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_DATE)""",
                    (merchant_id, category, name, variant, description, price, tags,
                     image_filename),
                )
        conn.commit()
        return len(KFC_MENU)
    finally:
        conn.close()


if __name__ == "__main__":
    from app import init_db

    init_db()
    print(f"Seeded {seed_kfc()} KFC menu variants.")
