import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from app import BASE_DIR, app, connect, init_db, recommend_menu_items, seed_db
from seed_kfc import seed_kfc
from seed_menus import seed_menus
from store_menus import IMAGE_QUERIES, STORE_MENUS


class StoreMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "test.db")
        app.config.update(TESTING=True, DATABASE=self.database)
        init_db(self.database)
        seed_db(self.database)
        seed_kfc(self.database)
        seed_menus(self.database)
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def merchant_id(self, name):
        db = connect(self.database)
        row = db.execute("SELECT id FROM merchants WHERE name=?", (name,)).fetchone()
        db.close()
        return row["id"]

    def test_menu_data_is_consistent(self):
        for name, store in STORE_MENUS.items():
            self.assertTrue(store["items"], name)
            for section, item, _variant, _desc, price, tags, image in store["items"]:
                self.assertIn(section, store["sections"], f"{name}: {item}")
                self.assertGreater(price, 0)
                self.assertTrue(tags)
                self.assertIn(image, IMAGE_QUERIES[store["slug"]], f"{name}: {image}")

    def test_every_store_has_a_menu_and_seeding_is_idempotent(self):
        db = connect(self.database)
        empty = db.execute("""
            SELECT m.name FROM merchants m
            WHERE NOT EXISTS (SELECT 1 FROM menu_items mi WHERE mi.merchant_id=m.id AND mi.is_active=1)
        """).fetchall()
        before = db.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
        db.close()
        self.assertEqual([row["name"] for row in empty], [])
        seed_menus(self.database)
        db = connect(self.database)
        after = db.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
        db.close()
        self.assertEqual(before, after)

    def test_store_page_groups_variants_and_uses_store_tabs(self):
        page = self.client.get(f"/store/{self.merchant_id('Pizza Hut Uganda')}").get_data(as_text=True)
        self.assertIn('id="pizza-hut-tab-pizzas"', page)
        self.assertIn('id="pizza-hut-category-meal-deals"', page)
        self.assertEqual(page.count("Pepperoni</h3>"), 1)
        self.assertIn(">Large</label>", page)
        self.assertIn("Not affiliated with Pizza Hut.", page)
        self.assertNotIn("KFC Uganda menu", page)

    def test_every_store_page_renders(self):
        db = connect(self.database)
        ids = [row["id"] for row in db.execute("SELECT id FROM merchants")]
        db.close()
        for merchant_id in ids:
            response = self.client.get(f"/store/{merchant_id}")
            self.assertEqual(response.status_code, 200)
            self.assertIn('class="product-card"', response.get_data(as_text=True))

    def test_homepage_shows_menu_counts_for_every_store(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn(">0 gifts<", page)
        self.assertIn("Java House", page)

    def test_recommender_now_covers_all_stores(self):
        db = connect(self.database)
        results = recommend_menu_items(db, "birthday cake", budget=100000)
        stores = {r["merchant"]["name"] for r in results}
        db.close()
        self.assertTrue(results)
        self.assertIn("Sweet Crumbs Bakery", stores)
        self.assertTrue(all(r["price"] <= 100000 for r in results))

    def test_menu_item_from_new_store_can_be_bought(self):
        db = connect(self.database)
        item = db.execute(
            "SELECT id, price_ugx FROM menu_items WHERE name='Cappuccino' AND variant='Double'"
        ).fetchone()
        db.close()
        response = self.client.get(f"/buy/menu/{item['id']}")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)
        response = self.client.post(f"/buy/menu/{item['id']}", data={
            "csrf_token": csrf, "sender_name": "A Person", "recipient_phone": "0770123456",
            "message": "", "payment_method": "airtel",
        })
        self.assertEqual(response.status_code, 302)

    def test_credits_page_lists_only_existing_photos(self):
        img = BASE_DIR / "static" / "img"
        credits_file = img / "credits.json"
        backup = credits_file.read_bytes() if credits_file.is_file() else None
        test_dir = img / "zz-test-store"
        try:
            test_dir.mkdir(exist_ok=True)
            (test_dir / "photo.jpg").write_bytes(b"jpg")
            credits_file.write_text(json.dumps({
                "zz-test-store/photo.jpg": {"store": "Test", "photographer": "Jane Doe",
                                            "photographer_url": "https://x", "page": "https://y",
                                            "source": "Pexels"},
                "zz-test-store/missing.jpg": {"store": "Test", "photographer": "Ghost",
                                              "photographer_url": "https://x", "page": "https://y",
                                              "source": "Pexels"},
            }))
            page = self.client.get("/credits").get_data(as_text=True)
            self.assertIn("Jane Doe", page)
            self.assertNotIn("Ghost", page)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
            if backup is None:
                credits_file.unlink(missing_ok=True)
            else:
                credits_file.write_bytes(backup)


if __name__ == "__main__":
    unittest.main()
