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
