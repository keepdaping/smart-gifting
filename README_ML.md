# ML / Data Mining component (CSC 3118)

Topic: Machine Learning (recommender evaluation) + Data Mining (anomaly detection).

## Setup (project root, next to kfc_menu.py)
    pip install -r requirements-ml.txt
    pip install sentence-transformers     # optional: enables the embedding models (one-time ~90 MB download)

## Reproduce every number
    python -m ml.evaluate                 # RQ1: recommender comparison -> ml/eval/results.md / .csv
    python -m ml.fraud.simulate           # synthetic data (seeded)
    python -m ml.fraud.detect             # RQ2: rules vs Isolation Forest -> ml/fraud/results.md, confusion.png, model.joblib
    python -m pytest -q                   # whole suite, incl. tests/test_ml.py and tests/test_ml_app.py

The offline evaluation (RQ1) uses the KFC menu only, because the gift-query relevance
labels name KFC items. The live app uses the same models over every merchant.

## How the app uses it (every merchant, not only KFC)

### Recommender: `GET /recommend?q=...&budget=...`
- `app.gift_catalogue(db)` lists everything a customer can buy right now: active menu
  items (e.g. KFC) and fixed gift products (e.g. Sweet Crumbs Bakery and the other
  stores). Products retired by a seed but kept for old vouchers are excluded.
- `app.recommend_gifts()` ranks them with `ml.service.rank()` (hybrid TF-IDF + LSA by
  default). Each result has `kind`, `merchant`, `price`, `image` and a `buy_url`.
- Products without hand-written tags get keywords from their merchant's category
  (`ml.catalog.CATEGORY_KEYWORDS`), so "headphones" finds electronics stores and
  "get well soon" finds pharmacies.
- Results are de-duplicated per (merchant, name): two stores can sell an item of the same name.
- The model cache is keyed on catalogue content, so price or menu changes take effect
  on the next request.
- `ML_RECOMMENDER` = `hybrid` (default) | `tfidf` | `lsa` | `embed` | `builtin`.
  Without scikit-learn the app falls back to its built-in TF-IDF ranker.

### Fraud check: cashier portal (`/merchant/verify`, `/merchant/redeem`)
The check is **advisory**. It warns the cashier, with reasons, before they redeem. It
never blocks a redemption. The score and flag are stored on the `REDEEMED` row of
`audit_log` (`risk_score`, `risk_flag`) and shown as "Flagged" in the audit trail.

How the six model features are computed from the database:

| Feature | Live definition |
|---|---|
| hours_since_purchase | now minus the voucher's `created_at` |
| device_redemptions_1h | vouchers for the same **recipient phone** redeemed in the last hour, at any store (not the cashier's till: a busy till is normal) |
| buyer_vouchers_24h | vouchers bought by the same sender name in the 24 h up to this purchase, at any store |
| failed_code_attempts | NOT_FOUND / WRONG_STORE lookups from this till at this store in the last 5 min |
| redeem_hour | hour now, East Africa Time |
| amount_ugx | voucher value, **normalised per merchant** (below) |

**Per-merchant amount normalisation.** The model learnt that about UGX 40,000 is a
normal amount. Before scoring, each amount is divided by the merchant's median price
and multiplied by that reference (`ml.fraud.detect.normalise_amount`). Without this
step, normal synthetic redemptions repriced to 3.5x KFC levels (bakery/electronics)
were flagged 8% of the time instead of 0.3%. With it, the false-positive rate is the
same at every price level.

`FRAUD_CHECK=0` turns the check off. If scikit-learn or `model.joblib` cannot be
loaded, the app uses the fixed rules in `ml/fraud/rules.py`, which have no dependencies.

## Use from Python
    from ml.service import suggest, rank
    suggest("lunch for my brother under 20k", mode="hybrid")          # KFC menu file
    rank("birthday cake", rows=[...catalogue dicts...], budget=130000)  # any merchants

    from ml.fraud.detect import FraudScorer
    FraudScorer().assess({...6 feature values...}, typical_amount_ugx=120000)

## Honest limitations (put these in the report)
- 43 gift queries were drafted for this prototype; relevance labels must be reviewed and ideally extended by real people (e.g. 10 classmates x 5 queries) to avoid author bias.
- Catalogue is small (41 KFC rows in the evaluation), so ranking differences are small; report bootstrap p-values, not just means.
- The offline evaluation covers KFC only. Rankings for the other merchants rely on short product descriptions and category keywords, and have not been evaluated with labelled queries.
- Fraud data is SYNTHETIC. Results show the method works on injected patterns, not real-world accuracy. For that reason the live check only advises the cashier.
- "Buyer" means the sender's name, because the app has no buyer accounts, so it is easy to evade.
- `model.joblib` is a pickle tied to the scikit-learn version that wrote it (1.9.1). Other versions print an `InconsistentVersionWarning`; re-run `python -m ml.fraud.detect` to rebuild it for the installed version.
