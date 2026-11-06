"""Offline evaluation of the recommenders on hand-labelled gift queries.
Run from project root:  python -m ml.evaluate
"""
import csv
import os
import numpy as np
from ml.catalog import load_catalog
from ml.metrics import precision_at_k, recall_at_k, reciprocal_rank, ndcg_at_k
from ml.recommenders import (TfidfRecommender, LsaRecommender,
                             EmbeddingRecommender, HybridRecommender, RandomRecommender)

HERE = os.path.dirname(__file__)
K = 5


def load_queries(path=os.path.join(HERE, "eval", "gift_queries.csv")):
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["query"], int(r["budget_ugx"]), set(r["relevant"].split("|")))
                for r in csv.DictReader(f)]


def build_models(items, use_embeddings=True):
    models = {"random (floor)": RandomRecommender(items)}
    tfidf = TfidfRecommender(items)
    lsa = LsaRecommender(items)
    models["tfidf (baseline)"] = tfidf
    models["lsa"] = lsa
    models["hybrid tfidf+lsa"] = HybridRecommender(tfidf, lsa, 0.5)
    if use_embeddings:
        try:
            emb = EmbeddingRecommender(items)
            models["embeddings"] = emb
            models["hybrid tfidf+embeddings"] = HybridRecommender(tfidf, emb, 0.5)
        except Exception as e:  # package or model weights not available
            print(f"[skip] embeddings unavailable ({type(e).__name__}); "
                  f"pip install sentence-transformers and run once with internet.")
    return models


def evaluate(models, items, queries):
    names = {it["name"] for it in items}
    min_price = {}
    for it in items:
        min_price[it["name"]] = min(min_price.get(it["name"], 10**9), it["price_ugx"])
    rows, per_query = [], {}
    for label, model in models.items():
        P, R, M, N = [], [], [], []
        for q, budget, rel in queries:
            bad = rel - names
            assert not bad, f"unknown item names in labels: {bad}"
            rel = {r for r in rel if min_price[r] <= budget}  # must be affordable
            if not rel:
                continue
            ranked = [it["name"] for it, _ in model.recommend(q, budget, K)]
            P.append(precision_at_k(ranked, rel, K)); R.append(recall_at_k(ranked, rel, K))
            M.append(reciprocal_rank(ranked, rel)); N.append(ndcg_at_k(ranked, rel, K))
        per_query[label] = np.array(N)
        rows.append((label, np.mean(P), np.mean(R), np.mean(M), np.mean(N), len(N)))
    return rows, per_query


def to_markdown(rows):
    out = [f"| Model | Precision@{K} | Recall@{K} | MRR | NDCG@{K} | Queries |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r[0]} | {r[1]:.3f} | {r[2]:.3f} | {r[3]:.3f} | {r[4]:.3f} | {r[5]} |")
    return "\n".join(out)


def paired_bootstrap(a, b, n=5000, seed=42):
    """P(mean(b) <= mean(a)) over query resamples. Small value = b reliably better."""
    rng = np.random.default_rng(seed)
    d = b - a
    idx = rng.integers(0, len(d), (n, len(d)))
    return float((d[idx].mean(axis=1) <= 0).mean())


def main():
    items = load_catalog()
    queries = load_queries()
    models = build_models(items)
    rows, pq = evaluate(models, items, queries)
    md = to_markdown(rows)
    print(md)
    base = pq["tfidf (baseline)"]
    lines = ["", "Per-query NDCG@5 vs baseline (wins / ties / losses, bootstrap p):"]
    for label, v in pq.items():
        if label == "tfidf (baseline)":
            continue
        w, t, l = int((v > base).sum()), int((v == base).sum()), int((v < base).sum())
        lines.append(f"- {label}: {w}/{t}/{l}, p = {paired_bootstrap(base, v):.3f}")
    print("\n".join(lines))
    with open(os.path.join(HERE, "eval", "results.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n" + "\n".join(lines) + "\n")
    with open(os.path.join(HERE, "eval", "results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", f"precision@{K}", f"recall@{K}", "mrr", f"ndcg@{K}", "queries"])
        w.writerows([[r[0], *[round(x, 4) for x in r[1:5]], r[5]] for r in rows])


if __name__ == "__main__":
    main()
