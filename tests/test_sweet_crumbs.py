import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from app import app, connect, init_db, seed_db


class SweetCrumbsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "test.db")
        app.config.update(TESTING=True, DATABASE=self.database)
        init_db(self.database)
        seed_db(self.database)
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def bakery(self):
        db = connect(self.database)
        merchant = db.execute(
            "SELECT id FROM merchants WHERE name='Sweet Crumbs Bakery'"
        ).fetchone()
        self.assertIsNotNone(merchant)
        return db, merchant["id"]

    def test_seed_command_is_idempotent_and_retires_unused_legacy_products(self):
        db, merchant_id = self.bakery()
        before = db.execute(
            "SELECT id, title FROM products WHERE merchant_id=? ORDER BY id",
            (merchant_id,),
        ).fetchall()
        self.assertEqual(len(before), 13)
        self.assertEqual(
            db.execute(
                "SELECT COUNT(*) FROM products WHERE merchant_id=? "
                "AND title IN ('Cupcake Box', 'Pastry Breakfast', 'Bread Basket')",
                (merchant_id,),
            ).fetchone()[0],
            0,
        )
        db.close()

        result = app.test_cli_runner().invoke(args=["seed-sweet-crumbs"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Seeded 13 Sweet Crumbs Bakery products.", result.output)

        db, merchant_id = self.bakery()
        after = db.execute(
            "SELECT id, title FROM products WHERE merchant_id=? ORDER BY id",
            (merchant_id,),
        ).fetchall()
        db.close()
        self.assertEqual([tuple(row) for row in before], [tuple(row) for row in after])

    def test_seed_preserves_retired_product_with_a_voucher(self):
        db, merchant_id = self.bakery()
        db.execute(
            "INSERT INTO products (merchant_id, title, monetary_value) "
            "VALUES (?, 'Bread Basket', 20000)",
            (merchant_id,),
        )
        product_id = db.execute(
            "SELECT id FROM products WHERE merchant_id=? AND title='Bread Basket'",
            (merchant_id,),
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO vouchers (voucher_code, merchant_id, product_id, sender_name, "
            "recipient_phone, monetary_value, price_at_purchase) "
            "VALUES ('GIFT-OLD-0001', ?, ?, 'A Person', '+256770123456', 20000, 20000)",
            (merchant_id, product_id),
        )
        db.commit()
        db.close()

        seed_db(self.database)
        db = connect(self.database)
        preserved = db.execute(
            "SELECT id FROM products WHERE merchant_id=? AND title='Bread Basket'",
            (merchant_id,),
        ).fetchone()
        voucher = db.execute(
            "SELECT product_id, price_at_purchase FROM vouchers "
            "WHERE voucher_code='GIFT-OLD-0001'"
        ).fetchone()
        db.close()
        self.assertEqual(preserved["id"], product_id)
        self.assertEqual(voucher["product_id"], product_id)
        self.assertEqual(voucher["price_at_purchase"], 20000)

    def test_store_and_every_product_image_are_available(self):
        db, merchant_id = self.bakery()
        products = db.execute(
            "SELECT image_url FROM products WHERE merchant_id=?", (merchant_id,)
        ).fetchall()
        db.close()
        self.assertEqual(len(products), 13)
        for product in products:
            self.assertTrue(product["image_url"])
            response = self.client.get(product["image_url"])
            self.assertEqual(response.status_code, 200, product["image_url"])
            self.assertTrue(response.mimetype.startswith("image/"))
            response.close()

        home = self.client.get("/").get_data(as_text=True)
        self.assertIn("Sweet Crumbs Bakery", home)
        self.assertIn("Proposed prices", home)
        page = self.client.get(f"/store/{merchant_id}").get_data(as_text=True)
        self.assertEqual(page.count('<article class="product-card">'), 13)
        self.assertIn(
            "Proposed demo prices pending confirmation from Sweet Crumbs Bakery",
            page,
        )
        self.assertIn("Chocolate Pudding Cake", page)

    def test_product_purchase_snapshot_and_cashier_redemption(self):
        db, merchant_id = self.bakery()
        product = db.execute(
            "SELECT id, title, monetary_value, description FROM products "
            "WHERE merchant_id=? AND title='Chocolate Pudding Cake'",
            (merchant_id,),
        ).fetchone()
        db.close()

        response = self.client.get(f"/buy/{product['id']}")
        self.assertIn(
            b"Proposed demo prices pending confirmation from Sweet Crumbs Bakery",
            response.data,
        )
        csrf = re.search(
            rb'name="csrf_token" value="([^"]+)"', response.data
        ).group(1).decode()
        response = self.client.post(f"/buy/{product['id']}", data={
            "csrf_token": csrf,
            "sender_name": "A Person",
            "recipient_phone": "0770123456",
            "message": "Enjoy",
            "payment_method": "mtn",
        })
        self.assertEqual(response.status_code, 302)
        code = urlparse(response.headers["Location"]).path.rsplit("/", 1)[-1]

        db = connect(self.database)
        db.execute(
            "UPDATE products SET monetary_value=monetary_value+5000 WHERE id=?",
            (product["id"],),
        )
        db.commit()
        voucher = db.execute(
            "SELECT product_id, menu_item_id, price_at_purchase, monetary_value "
            "FROM vouchers WHERE voucher_code=?",
            (code,),
        ).fetchone()
        db.close()
        self.assertEqual(voucher["product_id"], product["id"])
        self.assertIsNone(voucher["menu_item_id"])
        self.assertEqual(voucher["price_at_purchase"], product["monetary_value"])
        self.assertEqual(voucher["monetary_value"], product["monetary_value"])

        ticket = self.client.get(f"/voucher/{code}")
        self.assertIn(product["title"].encode(), ticket.data)
        self.assertIn(f"UGX {product['monetary_value']:,}".encode(), ticket.data)
        self.assertIn(b"Proposed demo prices pending confirmation", ticket.data)
        self.assertIn(b"Proposed demo price pending bakery confirmation", ticket.data)

        with self.client.session_transaction() as session:
            session["cashier"] = {
                "merchant_id": merchant_id,
                "name": "Sweet Crumbs Bakery",
            }
        checked = self.client.get(f"/merchant/verify?code={code}")
        self.assertIn(product["title"].encode(), checked.data)
        self.assertIn(product["description"].encode(), checked.data)
        self.assertIn(b"Proposed demo prices pending confirmation", checked.data)
        csrf = re.search(
            rb'name="csrf_token" value="([^"]+)"', checked.data
        ).group(1).decode()
        response = self.client.post("/merchant/redeem", data={
            "csrf_token": csrf,
            "voucher_code": code,
        })
        self.assertEqual(response.status_code, 302)

        db = connect(self.database)
        audit = db.execute(
            "SELECT outcome, cashier FROM audit_log WHERE voucher_code=? "
            "ORDER BY id DESC LIMIT 1",
            (code,),
        ).fetchone()
        voucher_status = db.execute(
            "SELECT status FROM vouchers WHERE voucher_code=?", (code,)
        ).fetchone()["status"]
        db.close()
        self.assertEqual(audit["outcome"], "REDEEMED")
        self.assertEqual(audit["cashier"], "Sweet Crumbs Bakery")
        self.assertEqual(voucher_status, "USED")


if __name__ == "__main__":
    unittest.main()
