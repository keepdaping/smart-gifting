import math
from ml.catalog import load_catalog
from ml.query import parse_budget, clean_query
from ml.metrics import precision_at_k, recall_at_k, reciprocal_rank, ndcg_at_k
from ml.recommenders import TfidfRecommender, LsaRecommender, HybridRecommender
from ml.fraud.simulate import simulate
from ml.service import suggest


def test_parse_budget():
    assert parse_budget("lunch under 20k") == 20000
    assert parse_budget("gift below 50,000 UGX") == 50000
    assert parse_budget("food for 5 friends") is None
    assert parse_budget("budget 35000 for my mum") == 35000


def test_metrics():
    assert precision_at_k(["a", "b", "c"], {"a", "c"}, 2) == 0.5
    assert recall_at_k(["a", "b"], {"a", "c"}, 2) == 0.5
    assert reciprocal_rank(["x", "a"], {"a"}) == 0.5
    assert math.isclose(ndcg_at_k(["a", "b"], {"a", "b"}, 2), 1.0)
    assert ndcg_at_k(["x"], {"a"}, 1) == 0.0


def test_catalog_complete():
    items = load_catalog()
    assert len(items) >= 40 and all(i["price_ugx"] > 0 for i in items)


def test_recommenders_respect_budget_and_dedupe():
    items = load_catalog()
    for rec in (TfidfRecommender(items), LsaRecommender(items)):
        out = rec.recommend("family dinner", budget=30000, k=5)
        names = [it["name"] for it, _ in out]
        assert len(names) == len(set(names))
        assert all(it["price_ugx"] <= 30000 for it, _ in out)


def test_deterministic():
    items = load_catalog()
    a = HybridRecommender(TfidfRecommender(items), LsaRecommender(items)).recommend("sweet treat", 20000)
    b = HybridRecommender(TfidfRecommender(items), LsaRecommender(items)).recommend("sweet treat", 20000)
    assert [x[0]["id"] for x in a] == [x[0]["id"] for x in b]


def test_fraud_simulation_reproducible():
    assert simulate(seed=1).equals(simulate(seed=1))
    assert 0.03 < simulate().is_fraud.mean() < 0.05


def test_service_parses_budget_from_text():
    out = suggest("lunch for my brother under 20k", mode="tfidf")
    assert out and all(r["price_ugx"] <= 20000 for r in out)


# --- multi-merchant catalogue -------------------------------------------------
from ml.catalog import items_from_dicts
from ml.service import get_recommender, rank


def _mixed_rows():
    return [
        dict(id=1, kind="menu_item", merchant_id=1, merchant_name="KFC", merchant_category="Food",
             category="Burgers", name="Zinger Burger", variant=None,
             description="Spicy chicken fillet burger", price_ugx=18000, tags="spicy chicken lunch"),
        dict(id=7, kind="product", merchant_id=2, merchant_name="Sweet Crumbs Bakery",
             merchant_category="Bakery", category="Bakery", name="Red Velvet Cupcake Box",
             description="A box of red velvet cupcakes for sharing.", price_ugx=45000),
        dict(id=8, kind="product", merchant_id=2, merchant_name="Sweet Crumbs Bakery",
             merchant_category="Bakery", category="Bakery", name="Celebration Cake",
             description="A chocolate cake gift for a special celebration.", price_ugx=120000),
        dict(id=9, kind="product", merchant_id=3, merchant_name="Java House",
             merchant_category="Coffee", category="Coffee", name="Celebration Cake",
             description="Cake and coffee for a celebration.", price_ugx=60000),
    ]


def test_items_from_dicts_keeps_merchant_and_kind():
    items = items_from_dicts(_mixed_rows())
    assert [i["merchant_id"] for i in items] == [1, 2, 2, 3]
    assert items[1]["kind"] == "product" and "Bakery" in items[1]["doc"]


def test_rank_finds_non_kfc_products_and_respects_budget():
    rows = _mixed_rows()
    out = rank("birthday cake", rows=rows, budget=100000, k=5, mode="tfidf")
    assert out and out[0]["name"] == "Celebration Cake" and out[0]["merchant_id"] == 3
    assert all(r["price_ugx"] <= 100000 for r in out)
    assert rank("cupcakes", rows=rows, mode="hybrid")[0]["merchant_name"] == "Sweet Crumbs Bakery"


def test_same_name_at_two_merchants_is_not_deduplicated():
    out = rank("celebration cake", rows=_mixed_rows(), k=5, mode="tfidf")
    cakes = [(r["merchant_id"], r["name"]) for r in out if r["name"] == "Celebration Cake"]
    assert sorted(cakes) == [(2, "Celebration Cake"), (3, "Celebration Cake")]


def test_recommender_cache_follows_catalogue_content():
    rows = _mixed_rows()
    first = get_recommender("tfidf", rows)
    assert get_recommender("tfidf", [dict(r) for r in rows]) is first
    changed = [dict(r) for r in rows]
    changed[1]["price_ugx"] = 50000          # same length, different content
    assert get_recommender("tfidf", changed) is not first


def test_rank_empty_query_returns_nothing():
    assert rank("   ", rows=_mixed_rows()) == []
