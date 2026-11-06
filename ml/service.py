"""Thin layer the Flask app calls. Keeps routes free of ML details."""
import hashlib

from ml.catalog import items_from_dicts, load_catalog
from ml.query import parse_budget, clean_query
from ml.recommenders import (TfidfRecommender, LsaRecommender,
                             EmbeddingRecommender, HybridRecommender)

MODES = ("tfidf", "lsa", "embed", "hybrid")
_cache = {}
_CACHE_SIZE = 8


def _fingerprint(items):
    """Content hash of the catalogue: a changed price, item or merchant gives a new key."""
    h = hashlib.sha1()
    for it in items:
        h.update(repr((it.get("kind"), it.get("merchant_id"), it["id"],
                       it["price_ugx"], it["doc"])).encode("utf-8"))
    return h.hexdigest()


def get_recommender(mode="hybrid", rows=None):
    """mode: tfidf | lsa | embed | hybrid.  rows: catalogue dicts from any merchant(s),
    or None = the KFC menu file."""
    if mode not in MODES:
        raise ValueError(f"unknown recommender mode {mode!r}; use one of {MODES}")
    items = items_from_dicts(rows) if rows else load_catalog()
    key = (mode, _fingerprint(items))
    if key in _cache:
        return _cache[key]
    tfidf = TfidfRecommender(items)
    if mode == "tfidf":
        rec = tfidf
    elif mode == "lsa":
        rec = LsaRecommender(items)
    else:
        try:
            sem = EmbeddingRecommender(items)
        except Exception:                      # embeddings not installed -> fall back to LSA
            sem = LsaRecommender(items)
        rec = sem if mode == "embed" else HybridRecommender(tfidf, sem, 0.5)
    if len(_cache) >= _CACHE_SIZE:             # catalogue changed many times: drop the oldest
        _cache.pop(next(iter(_cache)))
    _cache[key] = rec
    return rec


def rank(text, rows=None, budget=None, k=5, mode="hybrid"):
    """Rank items for a request whose budget the caller has already worked out."""
    query = clean_query(text) or text
    if not query.strip():
        return []
    rec = get_recommender(mode, rows)
    return [dict(it, score=round(s, 4)) for it, s in rec.recommend(query, budget, k)]


def suggest(text, mode="hybrid", rows=None, budget=None, k=5):
    """Natural-language request -> list of dicts. Budget is parsed from the text if not given."""
    budget = budget if budget is not None else parse_budget(text)
    return rank(text, rows=rows, budget=budget, k=k, mode=mode)
