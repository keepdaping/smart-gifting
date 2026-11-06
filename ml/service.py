"""Thin layer the Flask app calls. Keeps routes free of ML details."""
from ml.catalog import items_from_dicts, load_catalog
from ml.query import parse_budget, clean_query
from ml.recommenders import (TfidfRecommender, LsaRecommender,
                             EmbeddingRecommender, HybridRecommender)

_cache = {}


def get_recommender(mode="hybrid", rows=None):
    """mode: tfidf | lsa | embed | hybrid.  rows: list of MenuItem dicts (or None = menu file)."""
    key = (mode, len(rows) if rows else 0)
    if key in _cache:
        return _cache[key]
    items = items_from_dicts(rows) if rows else load_catalog()
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
    _cache[key] = rec
    return rec


def suggest(text, mode="hybrid", rows=None, budget=None, k=5):
    """Natural-language request -> list of dicts. Budget is parsed from the text if not given."""
    budget = budget if budget is not None else parse_budget(text)
    rec = get_recommender(mode, rows)
    return [dict(it, score=round(s, 4)) for it, s in rec.recommend(clean_query(text) or text, budget, k)]
