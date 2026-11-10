import tempfile
import unittest
from pathlib import Path

from app import app, init_db, seed_db
from seed_kfc import seed_kfc
from seed_menus import seed_menus


class AiPagesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = str(Path(self.temp_dir.name) / "test.db")
        app.config.update(TESTING=True, DATABASE=database)
        init_db(database)
        seed_db(database)
        seed_kfc(database)
        seed_menus(database)
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_homepage_has_gift_finder_wired_to_recommender(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="giftFinder"', page)
        self.assertIn('id="finderForm"', page)
        self.assertIn('data-finder-q="birthday gift for my mum under 50k"', page)
        self.assertIn('href="/ai"', page)

    def test_finder_example_queries_return_gifts_within_budget(self):
        for query, budget in [("birthday gift for my mum under 50k", 50000),
                              ("something for a student under 30k", 30000),
                              ("coffee date for two", None)]:
            data = self.client.get("/recommend", query_string={"q": query}).get_json()
            self.assertEqual(data["budget"], budget, query)
            self.assertTrue(data["recommendations"], query)
            for rec in data["recommendations"]:
                self.assertIn("buy_url", rec)
                if budget:
                    self.assertLessEqual(rec["price"], budget)

    def test_ai_page_shows_both_components_and_results(self):
        response = self.client.get("/ai")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Gift Recommender", page)
        self.assertIn("Fraud Check at the Till", page)
        self.assertIn("NDCG@5", page)
        self.assertIn("Isolation Forest", page)
        self.assertIn("Running in this app", page)
        self.assertIn("redemptions scored so far", page)

    def test_confusion_matrix_image_is_served(self):
        response = self.client.get("/ai/confusion.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        response.close()


if __name__ == "__main__":
    unittest.main()
