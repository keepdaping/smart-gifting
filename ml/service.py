"""Thin layer the Flask app calls. Keeps routes free of ML details.

Loading the sentence-transformers model (PyTorch + the model files) takes several
seconds, so the app builds it in a background thread. Until it is ready, searches are
answered by the TF-IDF + LSA hybrid, which is built in milliseconds.
"""
import hashlib
import logging
import threading

from ml.catalog import items_from_dicts, load_catalog
from ml.query import parse_budget, clean_query
from ml.recommenders import (TfidfRecommender, LsaRecommender,
                             EmbeddingRecommender, HybridRecommender)

MODES = ("tfidf", "lsa", "embed", "hybrid")
_cache = {}
_CACHE_SIZE = 8
_lock = threading.Lock()
_building = set()
log = logging.getLogger(__name__)


def _fingerprint(items):
    """Content hash of the catalogue: a changed price, item or merchant gives a new key."""
    h = hashlib.sha1()
    for it in items:
        h.update(repr((it.get("kind"), it.get("merchant_id"), it["id"],
                       it["price_ugx"], it["doc"])).encode("utf-8"))
    return h.hexdigest()


def _remember(key, rec):
    with _lock:
        if key not in _cache and len(_cache) >= _CACHE_SIZE:   # drop the oldest
            _cache.pop(next(iter(_cache)))
        _cache[key] = rec
    return rec


def _fast(mode, items, tfidf=None):
    """Models that build in milliseconds: no PyTorch involved."""
    tfidf = tfidf or TfidfRecommender(items)
    if mode == "tfidf":
        return tfidf
    lsa = LsaRecommender(items)
    if mode in ("lsa", "embed"):
        return lsa
    return HybridRecommender(tfidf, lsa, 0.5)


def _full(mode, items, local_only):
    if mode in ("tfidf", "lsa"):
        return _fast(mode, items)
    tfidf = TfidfRecommender(items)
    try:
        sem = EmbeddingRecommender(items, local_only=local_only)
    except Exception as exc:              # not installed or not downloaded -> LSA
        log.info("Embeddings unavailable (%s); using LSA as the semantic model.", exc)
        return _fast(mode, items, tfidf)
    return sem if mode == "embed" else HybridRecommender(tfidf, sem, 0.5)


def _build_in_background(key, mode, items):
    def work():
        try:
            _remember(key, _full(mode, items, local_only=True))
        finally:
            with _lock:
                _building.discard(key)

    with _lock:
        if key in _building or key in _cache:
            return
        _building.add(key)
    threading.Thread(target=work, name="recommender-warmup", daemon=True).start()


def get_recommender(mode="hybrid", rows=None, wait=True, local_only=False):
    """mode: tfidf | lsa | embed | hybrid.  rows: catalogue dicts from any merchant(s),
    or None = the KFC menu file.

    wait=False (used by the web app) never blocks on the embedding model: it starts
    loading it in the background and returns the fast TF-IDF + LSA model meanwhile.
    """
    if mode not in MODES:
        raise ValueError(f"unknown recommender mode {mode!r}; use one of {MODES}")
    items = items_from_dicts(rows) if rows else load_catalog()
    fingerprint = _fingerprint(items)
    key = (mode, fingerprint)
    with _lock:
        if key in _cache:
            return _cache[key]
    if mode in ("tfidf", "lsa"):
        return _remember(key, _fast(mode, items))
    if wait:
        return _remember(key, _full(mode, items, local_only))
    _build_in_background(key, mode, items)
    fast_key = ("fast-" + mode, fingerprint)
    with _lock:
        if fast_key in _cache:
            return _cache[fast_key]
    return _remember(fast_key, _fast(mode, items))


def warm_up(rows, mode="hybrid"):
    """Start loading the full model now, so the first real search is already fast."""
    if mode in ("embed", "hybrid"):
        get_recommender(mode, rows, wait=False)


def rank(text, rows=None, budget=None, k=5, mode="hybrid", wait=True):
    """Rank items for a request whose budget the caller has already worked out."""
    query = clean_query(text) or text
    if not query.strip():
        return []
    rec = get_recommender(mode, rows, wait=wait, local_only=not wait)
    return [dict(it, score=round(s, 4)) for it, s in rec.recommend(query, budget, k)]


def suggest(text, mode="hybrid", rows=None, budget=None, k=5):
    """Natural-language request -> list of dicts. Budget is parsed from the text if not given."""
    budget = budget if budget is not None else parse_budget(text)
    return rank(text, rows=rows, budget=budget, k=k, mode=mode)
