"""The ML recommender and fraud check inside the Flask app, across every merchant."""
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import app as app_module
from app import (app, assess_redemption, connect, fetch_voucher, gift_catalogue, init_db,
                 recommend_gifts, redemption_features, seed_db)
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


def frozen_datetime(moment):
    """A datetime class whose now() is fixed, so hour-of-day features are repeatable."""
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else moment.replace(tzinfo=None)
    return Frozen


EAT = timezone(timedelta(hours=3))
AFTERNOON = datetime(2026, 11, 6, 13, 0, tzinfo=EAT).astimezone(timezone.utc)
NIGHT = datetime(2026, 11, 6, 2, 0, tzinfo=EAT).astimezone(timezone.utc)
FMT = "%Y-%m-%d %H:%M:%S"


class FraudCheckAcrossMerchantsTests(MlAppTestCase):
    def add_voucher(self, code, merchant, title, created, sender="A Person",
                    phone="+256770123456"):
        merchant_id = self.merchant_id(merchant)
        db = connect(self.database)
        row = db.execute("SELECT id, price_ugx AS price FROM menu_items WHERE merchant_id=? AND name=?",
                         (merchant_id, title)).fetchone()
        column = "menu_item_id"
        if row is None:
            row = db.execute("SELECT id, monetary_value AS price FROM products "
                             "WHERE merchant_id=? AND title=?", (merchant_id, title)).fetchone()
            column = "product_id"
        db.execute(f"INSERT INTO vouchers (voucher_code, merchant_id, {column}, sender_name, "
                   "recipient_phone, monetary_value, price_at_purchase, created_at) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (code, merchant_id, row["id"], sender, phone, row["price"], row["price"],
                    created.strftime(FMT)))
        db.commit()
        db.close()
        return merchant_id

    def assess(self, code, merchant_id, now, client_key="till"):
        db = connect(self.database)
        with app.test_request_context(), \
                mock.patch.object(app_module, "datetime", frozen_datetime(now)):
            voucher = fetch_voucher(db, code)
            features = redemption_features(db, voucher, merchant_id, client_key)
            risk = assess_redemption(db, voucher, merchant_id, client_key)
        db.close()
        return features, risk

    def test_ordinary_redemptions_are_not_flagged_at_any_merchant(self):
        gifts = [("KFC", "Streetwise 2"), ("Sweet Crumbs Bakery", "Rainbow Layer Cake"),
                 ("TechHub Gadgets", "Wireless Earbuds"), ("Scoop & Smile Desserts", "Ice Cream Sundae")]
        for number, (merchant, title) in enumerate(gifts):
            with self.subTest(merchant=merchant):
                code = f"GIFT-OKAY-000{number}"
                merchant_id = self.add_voucher(code, merchant, title, AFTERNOON - timedelta(hours=30),
                                               sender=f"Sender {number}", phone=f"+25677000000{number}")
                features, risk = self.assess(code, merchant_id, AFTERNOON)
                self.assertEqual(features["redeem_hour"], 13)
                self.assertAlmostEqual(features["hours_since_purchase"], 30.0)
                self.assertEqual(risk["method"], "isolation_forest")
                self.assertFalse(risk["suspicious"], risk)

    def test_features_count_recipient_sender_and_failed_attempts(self):
        created = NIGHT - timedelta(minutes=10)
        bakery = self.add_voucher("GIFT-FEAT-0000", "Sweet Crumbs Bakery", "Celebration Cake", created,
                                  sender="Mallory", phone="+256770999999")
        kfc = self.merchant_id("KFC")
        db = connect(self.database)
        for i in range(1, 4):  # same sender (any case), another store, same recipient, redeemed
            db.execute("INSERT INTO vouchers (voucher_code, merchant_id, sender_name, recipient_phone, "
                       "monetary_value, status, created_at) VALUES (?, ?, 'mallory', '+256770999999', "
                       "20000, 'USED', ?)",
                       (f"GIFT-FEAT-000{i}", kfc, (created - timedelta(hours=i)).strftime(FMT)))
            db.execute("INSERT INTO audit_log (voucher_code, merchant_id, outcome, created_at) "
                       "VALUES (?, ?, 'REDEEMED', ?)",
                       (f"GIFT-FEAT-000{i}", kfc, (NIGHT - timedelta(minutes=5 * i)).strftime(FMT)))
        for _ in range(2):
            db.execute("INSERT INTO audit_log (voucher_code, merchant_id, outcome, created_at, client_key) "
                       "VALUES ('GIFT-NOPE-NOPE', ?, 'NOT_FOUND', ?, 'till')",
                       (bakery, (NIGHT - timedelta(minutes=1)).strftime(FMT)))
        db.commit()
        db.close()
        features, _risk = self.assess("GIFT-FEAT-0000", bakery, NIGHT)
        self.assertEqual(features["device_redemptions_1h"], 3)
        self.assertEqual(features["buyer_vouchers_24h"], 4)
        self.assertEqual(features["failed_code_attempts"], 2)
        self.assertEqual(features["redeem_hour"], 2)
        self.assertEqual(features["amount_ugx"], 120000)

    def stage_suspicious_bakery_voucher(self):
        """A code bought minutes ago by a sender who just bought many, redeemed at 2am."""
        created = NIGHT - timedelta(minutes=5)
        bakery = self.add_voucher("GIFT-RISK-0000", "Sweet Crumbs Bakery", "Celebration Cake", created,
                                  sender="Mallory", phone="+256770999999")
        db = connect(self.database)
        for i in range(1, 10):
            db.execute("INSERT INTO vouchers (voucher_code, merchant_id, sender_name, recipient_phone, "
                       "monetary_value, created_at) VALUES (?, ?, 'Mallory', '+256770999999', 45000, ?)",
                       (f"GIFT-RISK-{i:04d}", bakery, (created - timedelta(minutes=i)).strftime(FMT)))
        db.commit()
        db.close()
        return bakery

    def test_suspicious_redemption_is_flagged_shown_and_recorded(self):
        bakery = self.stage_suspicious_bakery_voucher()
        with mock.patch.object(app_module, "datetime", frozen_datetime(NIGHT)):
            with self.client.session_transaction() as session:
                session["cashier"] = {"merchant_id": bakery, "name": "Sweet Crumbs Bakery"}
            page = self.client.get("/merchant/verify?code=GIFT-RISK-0000").get_data(as_text=True)
            self.assertIn("data-fraud-flag", page)
            self.assertIn("sender bought 10 vouchers in 24 h", page)
            csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
            response = self.client.post("/merchant/redeem", follow_redirects=True,
                                        data={"csrf_token": csrf, "voucher_code": "GIFT-RISK-0000"})
        html = response.get_data(as_text=True)
        self.assertIn("GIFT-RISK-0000 redeemed", html)          # advisory: never blocks
        self.assertIn("Fraud check flagged this redemption", html)
        self.assertIn("Flagged", html)
        db = connect(self.database)
        row = db.execute("SELECT risk_flag, risk_score, client_key FROM audit_log "
                         "WHERE voucher_code='GIFT-RISK-0000' AND outcome='REDEEMED'").fetchone()
        status = db.execute("SELECT status FROM vouchers WHERE voucher_code='GIFT-RISK-0000'").fetchone()[0]
        db.close()
        self.assertEqual((row["risk_flag"], status), (1, "USED"))
        self.assertGreater(row["risk_score"], 0)
        self.assertTrue(row["client_key"])

    def test_rules_are_used_when_the_model_is_unavailable(self):
        bakery = self.stage_suspicious_bakery_voucher()
        with mock.patch.object(app_module, "_fraud_scorer", False):
            _features, risk = self.assess("GIFT-RISK-0000", bakery, NIGHT)
        self.assertEqual(risk["method"], "rules")
        self.assertTrue(risk["suspicious"])
        self.assertIn("sender bought 10 vouchers in 24 h", risk["reasons"])

    def test_fraud_check_can_be_switched_off(self):
        bakery = self.stage_suspicious_bakery_voucher()
        with mock.patch.object(app_module, "FRAUD_CHECK", False):
            _features, risk = self.assess("GIFT-RISK-0000", bakery, NIGHT)
        self.assertIsNone(risk)


if __name__ == "__main__":
    unittest.main()
