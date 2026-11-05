import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from app import app, connect, init_db, recommend_menu_items, seed_db
from kfc_menu import KFC_MENU
from seed_kfc import seed_kfc


class KfcMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "test.db")
        app.config.update(TESTING=True, DATABASE=self.database)
        init_db(self.database)
        seed_db(self.database)
        seed_kfc(self.database)
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_is_idempotent(self):
        db = connect(self.database)
        before = db.execute(
            "SELECT id, name, variant, price_ugx, price_updated_at "
            "FROM menu_items ORDER BY id"
        ).fetchall()
        db.execute("UPDATE menu_items SET image_filename=NULL WHERE id=1")
        db.commit()
        db.close()

        self.assertEqual(seed_kfc(self.database), len(KFC_MENU))

        db = connect(self.database)
        after = db.execute(
            "SELECT id, name, variant, price_ugx, price_updated_at, image_filename "
            "FROM menu_items ORDER BY id"
        ).fetchall()
        merchant_count = db.execute(
            "SELECT COUNT(*) FROM merchants WHERE name='KFC'"
        ).fetchone()[0]
        db.close()
        self.assertEqual([tuple(row) for row in before], [
            tuple(row)[0:5] for row in after
        ])
        self.assertEqual(after[0]["image_filename"], f"kfc/{KFC_MENU[0][-1]}.jpg")
        self.assertEqual(len(after), len(KFC_MENU))
        self.assertEqual(merchant_count, 1)
        command = app.test_cli_runner().invoke(args=["seed-kfc"])
        self.assertEqual(command.exit_code, 0, command.output)

    def test_every_kfc_menu_item_has_a_local_image(self):
        db = connect(self.database)
        items = db.execute("""
            SELECT mi.name, mi.variant, mi.image_filename
            FROM menu_items mi JOIN merchants m ON m.id=mi.merchant_id
            WHERE m.name='KFC'
        """).fetchall()
        db.close()
        self.assertEqual(len(items), len(KFC_MENU))
        for item in items:
            image_path = Path("static/img") / (item["image_filename"] or "")
            self.assertTrue(
                item["image_filename"] and image_path.is_file(),
                f"Missing image for {item['name']} {item['variant']}: {image_path}",
            )

    def test_check_kfc_images_cli_reports_missing_images(self):
        runner = app.test_cli_runner()
        result = runner.invoke(args=["check-kfc-images"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f"All {len(KFC_MENU)} active menu item image(s) exist.", result.output)

        db = connect(self.database)
        db.execute(
            "UPDATE menu_items SET image_filename='kfc/not-found.jpg' "
            "WHERE id=(SELECT MIN(id) FROM menu_items)"
        )
        db.commit()
        db.close()
        result = runner.invoke(args=["check-kfc-images"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("kfc/not-found.jpg", result.output)

    def test_existing_value_product_purchase_still_works(self):
        db = connect(self.database)
        product = db.execute(
            "SELECT id, monetary_value FROM products ORDER BY id LIMIT 1"
        ).fetchone()
        db.close()
        response = self.client.get(f"/buy/{product['id']}")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)
        response = self.client.post(f"/buy/{product['id']}", data={
            "csrf_token": csrf,
            "sender_name": "A Person",
            "recipient_phone": "0770123456",
            "message": "",
            "payment_method": "mtn",
        })
        self.assertEqual(response.status_code, 302)
        code = urlparse(response.headers["Location"]).path.rsplit("/", 1)[-1]
        db = connect(self.database)
        voucher = db.execute(
            "SELECT product_id, menu_item_id, price_at_purchase "
            "FROM vouchers WHERE voucher_code=?", (code,)
        ).fetchone()
        db.close()
        self.assertEqual(voucher["product_id"], product["id"])
        self.assertIsNone(voucher["menu_item_id"])
        self.assertEqual(voucher["price_at_purchase"], product["monetary_value"])

    def test_kfc_store_groups_items_by_name_and_uses_neutral_missing_image(self):
        db = connect(self.database)
        merchant_id = db.execute(
            "SELECT id FROM merchants WHERE name='KFC'"
        ).fetchone()["id"]
        expected_cards = db.execute(
            "SELECT COUNT(DISTINCT category || '|' || name) FROM menu_items "
            "WHERE merchant_id=? AND is_active=1", (merchant_id,)
        ).fetchone()[0]
        item_id = db.execute(
            "SELECT id FROM menu_items WHERE merchant_id=? ORDER BY id LIMIT 1",
            (merchant_id,),
        ).fetchone()["id"]
        db.execute(
            "UPDATE menu_items SET image_filename='kfc/missing-photo.jpg' WHERE id=?",
            (item_id,),
        )
        db.commit()
        db.close()

        page = self.client.get(f"/store/{merchant_id}").get_data(as_text=True)
        self.assertEqual(page.count('<article class="product-card">'), expected_cards)
        self.assertIn("Wings", page)
        self.assertIn("Streetwise", page)
        self.assertIn("UGX 56,000", page)
        self.assertIn('id="kfc-tab-burgers-wraps"', page)
        self.assertIn('id="kfc-category-burgers-wraps"', page)
        self.assertEqual(page.count('loading="eager"'), expected_cards - 1)
        self.assertIn("Demo data from KFC Uganda menu. Prices may vary by branch. Not affiliated with KFC.", page)
        self.assertNotIn("/static/img/kfc/missing-photo.jpg", page)
        self.assertIn("background:#f1f3f2", page)

    def test_purchase_snapshots_price_and_redemption_is_audited(self):
        db = connect(self.database)
        item = db.execute(
            "SELECT * FROM menu_items ORDER BY id LIMIT 1"
        ).fetchone()
        original_price = item["price_ugx"]
        db.close()

        response = self.client.get(f"/buy/menu/{item['id']}")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)
        response = self.client.post(f"/buy/menu/{item['id']}", data={
            "csrf_token": csrf,
            "sender_name": "A Person",
            "recipient_phone": "0770123456",
            "message": "Enjoy",
            "payment_method": "mtn",
        })
        self.assertEqual(response.status_code, 302)
        voucher_path = urlparse(response.headers["Location"]).path
        code = voucher_path.rsplit("/", 1)[-1]

        db = connect(self.database)
        db.execute(
            "UPDATE menu_items SET price_ugx=? WHERE id=?",
            (original_price + 5000, item["id"]),
        )
        db.commit()
        voucher = db.execute(
            "SELECT * FROM vouchers WHERE voucher_code=?", (code,)
        ).fetchone()
        self.assertIsNone(voucher["product_id"])
        self.assertEqual(voucher["menu_item_id"], item["id"])
        self.assertEqual(voucher["price_at_purchase"], original_price)
        self.assertEqual(voucher["monetary_value"], original_price)
        db.close()
        voucher_page = self.client.get(f"/voucher/{code}").get_data(as_text=True)
        self.assertIn(f"UGX {original_price:,}", voucher_page)

        with self.client.session_transaction() as session:
            db = connect(self.database)
            merchant = db.execute(
                "SELECT id FROM merchants WHERE name='KFC'"
            ).fetchone()
            db.close()
            session["cashier"] = {"merchant_id": merchant["id"], "name": "KFC"}
        response = self.client.get("/merchant/verify")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)
        self.client.post("/merchant/redeem", data={"csrf_token": csrf, "voucher_code": code})

        db = connect(self.database)
        redemption = db.execute(
            "SELECT * FROM audit_log WHERE voucher_code=? AND outcome='REDEEMED'",
            (code,),
        ).fetchone()
        self.assertEqual(redemption["menu_item_id"], item["id"])
        self.assertEqual(redemption["cashier"], "KFC")
        self.assertTrue(redemption["created_at"])
        db.close()
        verification = self.client.get(f"/merchant/verify?code={code}").get_data(as_text=True)
        self.assertIn(item["name"], verification)
        self.assertIn(item["variant"] or "", verification)
        self.assertIn(item["description"] or "", verification)

    def test_recommendations_apply_explicit_and_detected_budgets(self):
        response = self.client.get("/recommend?q=spicy%20under%2020000")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["budget"], 20000)
        self.assertTrue(data["recommendations"])
        for recommendation in data["recommendations"]:
            self.assertLessEqual(recommendation["price"], 20000)
            self.assertIn("item", recommendation)
            self.assertIn("merchant", recommendation)
            self.assertIn("image", recommendation)

        db = connect(self.database)
        with app.test_request_context("/"):
            recommendations = recommend_menu_items(db, "spicy", budget=15000)
        db.close()
        self.assertTrue(recommendations)
        self.assertTrue(all(result["price"] <= 15000 for result in recommendations))

    def test_migration_makes_legacy_product_optional_and_preserves_vouchers(self):
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        conn = sqlite3.connect(legacy_path)
        conn.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                category TEXT NOT NULL, image_url TEXT, description TEXT
            );
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT, merchant_id INTEGER NOT NULL,
                title TEXT NOT NULL, monetary_value INTEGER NOT NULL,
                description TEXT, image_url TEXT,
                FOREIGN KEY (merchant_id) REFERENCES merchants (id)
            );
            CREATE TABLE vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_code TEXT UNIQUE NOT NULL,
                merchant_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL, recipient_phone TEXT NOT NULL, message TEXT,
                monetary_value INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'USED')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            );
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_code TEXT NOT NULL,
                merchant_id INTEGER NOT NULL, outcome TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (merchant_id) REFERENCES merchants (id)
            );
            INSERT INTO merchants (id, name, category) VALUES (1, 'Old Store', 'Food');
            INSERT INTO products (id, merchant_id, title, monetary_value)
                VALUES (1, 1, 'Old Gift', 25000);
            INSERT INTO vouchers (
                id, voucher_code, merchant_id, product_id, sender_name,
                recipient_phone, monetary_value
            ) VALUES (1, 'GIFT-ABCD-EFGH', 1, 1, 'Sender', '+256770123456', 25000);
        """)
        conn.close()

        init_db(legacy_path)
        db = connect(legacy_path)
        product_id = {
            row["name"]: row for row in db.execute("PRAGMA table_info(vouchers)")
        }["product_id"]
        voucher = db.execute(
            "SELECT product_id, price_at_purchase FROM vouchers WHERE id=1"
        ).fetchone()
        db.close()
        self.assertEqual(product_id["notnull"], 0)
        self.assertEqual(voucher["product_id"], 1)
        self.assertEqual(voucher["price_at_purchase"], 25000)


if __name__ == "__main__":
    unittest.main()
