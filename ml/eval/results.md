| Model | Precision@5 | Recall@5 | MRR | NDCG@5 | Queries |
|---|---|---|---|---|---|
| random (floor) | 0.195 | 0.442 | 0.391 | 0.321 | 43 |
| tfidf (baseline) | 0.335 | 0.748 | 0.796 | 0.730 | 43 |
| lsa | 0.349 | 0.775 | 0.776 | 0.743 | 43 |
| hybrid tfidf+lsa | 0.349 | 0.775 | 0.777 | 0.745 | 43 |

Per-query NDCG@5 vs baseline (wins / ties / losses, bootstrap p):
- random (floor): 8/2/33, p = 1.000
- lsa: 7/32/4, p = 0.240
- hybrid tfidf+lsa: 6/34/3, p = 0.188
