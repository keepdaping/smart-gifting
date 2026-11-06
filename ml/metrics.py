"""Ranking metrics with binary relevance. `ranked` = list of names, `relevant` = set of names."""
import math


def precision_at_k(ranked, relevant, k):
    return sum(1 for r in ranked[:k] if r in relevant) / k


def recall_at_k(ranked, relevant, k):
    return sum(1 for r in ranked[:k] if r in relevant) / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked, relevant):
    for i, r in enumerate(ranked, 1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, relevant, k):
    dcg = sum(1.0 / math.log2(i + 1) for i, r in enumerate(ranked[:k], 1) if r in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0
