"""A slow-loading embedding model must never hold up a gift search."""
import time

import numpy as np

import ml.service as service
from ml.recommenders import HybridRecommender, LsaRecommender

ROWS = [
    {"id": 1, "kind": "menu_item", "merchant_id": 1, "category": "Cakes", "name": "Chocolate Cake",
     "variant": None, "description": "Rich chocolate birthday cake", "price_ugx": 40000, "tags": "cake birthday"},
    {"id": 2, "kind": "menu_item", "merchant_id": 2, "category": "Coffee", "name": "Cappuccino",
     "variant": None, "description": "Hot coffee with milk", "price_ugx": 9000, "tags": "coffee hot"},
    {"id": 3, "kind": "menu_item", "merchant_id": 3, "category": "Tech", "name": "Earbuds",
     "variant": None, "description": "Wireless earbuds", "price_ugx": 120000, "tags": "music audio"},
]


class SlowEmbeddings:
    """Stands in for sentence-transformers: takes seconds to load, like PyTorch does."""
    name = "embed"
    load_seconds = 1.5

    def __init__(self, items, local_only=False):
        time.sleep(self.load_seconds)
        self.items = items
        self.local_only = local_only

    def scores(self, query):
        return np.ones(len(self.items))


def test_search_does_not_wait_for_the_embedding_model(monkeypatch):
    monkeypatch.setattr(service, "EmbeddingRecommender", SlowEmbeddings)
    monkeypatch.setattr(service, "_cache", {})
    rows = [dict(r, description=r["description"] + " v1") for r in ROWS]

    started = time.perf_counter()
    results = service.rank("birthday cake", rows=rows, budget=50000, k=3, wait=False)
    assert time.perf_counter() - started < SlowEmbeddings.load_seconds / 2
    assert results and results[0]["name"] == "Chocolate Cake"

    deadline = time.time() + 10
    full = None
    while time.time() < deadline:
        full = service.get_recommender("hybrid", rows, wait=False)
        if isinstance(full, HybridRecommender) and isinstance(full.sem, SlowEmbeddings):
            break
        time.sleep(0.1)
    assert isinstance(full.sem, SlowEmbeddings), "background build should finish and be used"
    assert full.sem.local_only is True, "the web app must never download the model"


def test_missing_model_falls_back_to_lsa_without_retrying(monkeypatch):
    calls = []

    def unavailable(items, local_only=False):
        calls.append(local_only)
        raise OSError("model not downloaded")

    monkeypatch.setattr(service, "EmbeddingRecommender", unavailable)
    monkeypatch.setattr(service, "_cache", {})
    rows = [dict(r, description=r["description"] + " v2") for r in ROWS]

    service.rank("coffee", rows=rows, k=2, wait=False)
    deadline = time.time() + 5
    while time.time() < deadline and ("hybrid", service._fingerprint(service.items_from_dicts(rows))) not in service._cache:
        time.sleep(0.05)
    rec = service.get_recommender("hybrid", rows, wait=False)
    assert isinstance(rec.sem, LsaRecommender)
    for _ in range(3):
        service.rank("coffee", rows=rows, k=2, wait=False)
    assert calls == [True], "a missing model is looked up once, not on every search"
