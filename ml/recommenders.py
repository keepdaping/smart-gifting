"""Three gift recommenders behind one interface.

  TfidfRecommender      baseline: TF-IDF + cosine similarity (lexical)
  LsaRecommender        TF-IDF -> TruncatedSVD (Latent Semantic Analysis)
  EmbeddingRecommender  sentence-transformers (needs one-time model download)
  HybridRecommender     alpha * lexical + (1 - alpha) * semantic
"""
import hashlib
import os
import zlib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize


def _minmax(v):
    lo, hi = float(v.min()), float(v.max())
    return np.zeros_like(v) if hi - lo < 1e-12 else (v - lo) / (hi - lo)


class BaseRecommender:
    name = "base"

    def __init__(self, items):
        self.items = items

    def scores(self, query):
        raise NotImplementedError

    def recommend(self, query, budget=None, k=5):
        """Rank, apply the budget filter AFTER ranking, one result per product per merchant.

        Two merchants may sell items with the same name, so the de-duplication key
        includes merchant_id (None for the single-merchant KFC evaluation catalogue).
        """
        s = self.scores(query)
        order = np.argsort(-s, kind="stable")
        seen, out = set(), []
        for i in order:
            it = self.items[i]
            if budget is not None and it["price_ugx"] > budget:
                continue
            key = (it.get("merchant_id"), it["name"])
            if key in seen:
                continue
            seen.add(key)
            out.append((it, float(s[i])))
            if len(out) == k:
                break
        return out


class TfidfRecommender(BaseRecommender):
    name = "tfidf"

    def __init__(self, items):
        super().__init__(items)
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.X = self.vec.fit_transform([it["doc"] for it in items])

    def scores(self, query):
        q = self.vec.transform([query])
        return (self.X @ q.T).toarray().ravel()


class LsaRecommender(BaseRecommender):
    name = "lsa"

    def __init__(self, items, n_components=15, seed=42):
        super().__init__(items)
        self.vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        X = self.vec.fit_transform([it["doc"] for it in items])
        n = max(2, min(n_components, X.shape[1] - 1, X.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=n, random_state=seed)
        self.Z = normalize(self.svd.fit_transform(X))

    def scores(self, query):
        q = normalize(self.svd.transform(self.vec.transform([query])))
        return (self.Z @ q.T).ravel()


def load_sentence_model(model, local_only=False):
    """Load a sentence-transformers model.

    local_only=True never touches the internet: it uses the copy already downloaded
    (``flask --app app download-model``) and raises if there is none. The web app uses
    this so a slow or missing connection can never hold up a search.
    """
    from sentence_transformers import SentenceTransformer  # optional dependency
    if not local_only:
        return SentenceTransformer(model)
    try:
        return SentenceTransformer(model, local_files_only=True)
    except TypeError:  # older sentence-transformers without local_files_only
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        return SentenceTransformer(model)


class EmbeddingRecommender(BaseRecommender):
    name = "embed"

    def __init__(self, items, model="sentence-transformers/all-MiniLM-L6-v2",
                 cache_dir="ml", local_only=False):
        super().__init__(items)
        self.model = load_sentence_model(model, local_only)
        docs = [it["doc"] for it in items]
        # One cache file per catalogue content (not just its length), so a catalogue
        # with different items or merchants never reuses another's embeddings.
        digest = hashlib.sha1("\n".join([model, *docs]).encode("utf-8")).hexdigest()[:16]
        cache = os.path.join(cache_dir, f".embed_cache_{digest}.npy") if cache_dir else None
        if cache and os.path.exists(cache):
            self.E = np.load(cache)
        else:
            self.E = self.model.encode(docs, normalize_embeddings=True)
            if cache:
                np.save(cache, self.E)

    def scores(self, query):
        q = self.model.encode([query], normalize_embeddings=True)[0]
        return self.E @ q


class HybridRecommender(BaseRecommender):
    def __init__(self, lexical, semantic, alpha=0.5):
        super().__init__(lexical.items)
        self.lex, self.sem, self.alpha = lexical, semantic, alpha
        self.name = f"hybrid({lexical.name}+{semantic.name})"

    def scores(self, query):
        return self.alpha * _minmax(self.lex.scores(query)) + \
               (1 - self.alpha) * _minmax(self.sem.scores(query))


class RandomRecommender(BaseRecommender):
    """Sanity-check floor: any real model must beat this."""
    name = "random"

    def __init__(self, items, seed=42):
        super().__init__(items)
        self.seed = seed

    def scores(self, query):
        return np.random.default_rng(zlib.crc32(query.encode()) ^ self.seed).random(len(self.items))
