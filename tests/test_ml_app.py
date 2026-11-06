"""The ML recommender and fraud check inside the Flask app, across every merchant."""
import tempfile
import unittest
from pathlib import Path

from app import app, connect, gift_catalogue, init_db, recommend_gifts, seed_db
from catalogue import MERCHANTS
from seed_kfc import seed_kfc


class MlAppTestCase(unittest.TestCase):
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

    def merchant_id(self, name):
        db = connect(self.database)
        row = db.execute("SELECT id FROM merchants WHERE name=?", (name,)).fetchone()
        db.close()
        return row["id"]


class RecommenderAcrossMerchantsTests(MlAppTestCase):
    def test_catalogue_covers_every_merchant_once(self):
        with app.test_request_context():
            db = connect(self.database)
            rows = gift_catalogue(db)
            db.close()
        merchants = {row["merchant_name"] for row in rows}
        self.assertEqual(merchants, {m["name"] for m in MERCHANTS})
        kinds = {(row["merchant_name"], row["kind"]) for row in rows}
        self.assertIn(("KFC", "menu_item"), kinds)
        self.assertNotIn(("KFC", "product"), kinds)
        self.assertIn(("Sweet Crumbs Bakery", "product"), kinds)

    def test_retired_product_kept_for_a_voucher_is_not_recommended(self):
        bakery = self.merchant_id("Sweet Crumbs Bakery")
        db = connect(self.database)
        db.execute("INSERT INTO products (merchant_id, title, monetary_value, description) "
                   "VALUES (?, 'Bread Basket', 20000, 'Fresh bread for breakfast')", (bakery,))
        db.commit()
        with app.test_request_context():
            names = {row["name"] for row in gift_catalogue(db)}
            results = recommend_gifts(db, "bread basket breakfast", limit=20)
        db.close()
        self.assertNotIn("Bread Basket", names)
        self.assertNotIn("Bread Basket", [r["item"]["name"] for r in results])

    def test_cake_request_returns_bakery_products_with_buy_links(self):
        response = self.client.get("/recommend?q=birthday%20cake%20under%20130k")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["budget"], 130000)
        top = data["recommendations"][0]
        self.assertEqual(top["merchant"]["name"], "Sweet Crumbs Bakery")
        self.assertEqual(top["kind"], "product")
        self.assertTrue(top["buy_url"].startswith("/buy/"))
        self.assertTrue(top["image"].startswith("/assets/images/"))
        self.assertTrue(all(r["price"] <= 130000 for r in data["recommendations"]))
        self.assertEqual(self.client.get(top["buy_url"]).status_code, 200)

    def test_kfc_request_still_returns_menu_items(self):
        data = self.client.get("/recommend?q=spicy%20chicken%20under%2020000").get_json()
        top = data["recommendations"][0]
        self.assertEqual((top["merchant"]["name"], top["kind"]), ("KFC", "menu_item"))
        self.assertTrue(top["buy_url"].startswith("/buy/menu/"))

    def test_every_merchant_is_reachable_by_its_name(self):
        for merchant in MERCHANTS:
            with self.subTest(merchant=merchant["name"]):
                data = self.client.get("/recommend", query_string={"q": merchant["name"]}).get_json()
                self.assertIn(merchant["name"],
                              [r["merchant"]["name"] for r in data["recommendations"][:5]])

    def test_builtin_fallback_covers_other_merchants(self):
        db = connect(self.database)
        with app.test_request_context():
            results = recommend_gifts(db, "coffee for two", mode="builtin")
        db.close()
        self.assertTrue(results)
        self.assertIn(results[0]["merchant"]["name"], {"Java House", "Kampala Coffee Collective"})

    def test_untagged_products_are_found_through_category_keywords(self):
        cases = {"headphones": "Electronics", "get well soon": "Pharmacy",
                 "a gift for my sister who loves sweets": "Bakery"}
        db = connect(self.database)
        categories = dict(db.execute("SELECT name, category FROM merchants").fetchall())
        db.close()
        for query, category in cases.items():
            with self.subTest(query=query):
                data = self.client.get("/recommend", query_string={"q": query}).get_json()
                self.assertEqual(categories[data["recommendations"][0]["merchant"]["name"]], category)

    def test_nonsense_query_returns_nothing(self):
        data = self.client.get("/recommend?q=zzqxv").get_json()
        self.assertEqual(data["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
