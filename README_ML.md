# ML / Data Mining component (CSC 3118)

Topic: Machine Learning (recommender evaluation) + Data Mining (anomaly detection).

## Setup (project root, next to kfc_menu.py)
    pip install -r requirements-ml.txt
    pip install sentence-transformers     # optional: enables the embedding models (one-time ~90 MB download)

## Reproduce every number
    python -m ml.evaluate                 # RQ1: recommender comparison -> ml/eval/results.md / .csv
    python -m ml.fraud.simulate           # synthetic data (seeded)
    python -m ml.fraud.detect             # RQ2: rules vs Isolation Forest -> ml/fraud/results.md, confusion.png, model.joblib
    python -m pytest -q                   # 7 tests

## Use in Flask
    from ml.service import suggest
    suggest("lunch for my brother under 20k", mode="hybrid", rows=[...MenuItem dicts...])

    from ml.fraud.detect import FraudScorer
    FraudScorer().is_suspicious({...6 feature values...})

## Honest limitations (put these in the report)
- 43 gift queries were drafted for this prototype; relevance labels must be reviewed and ideally extended by real people (e.g. 10 classmates x 5 queries) to avoid author bias.
- Catalogue is small (41 rows), so ranking differences are small; report bootstrap p-values, not just means.
- Fraud data is SYNTHETIC. Results show the method works on injected patterns, not real-world accuracy.
