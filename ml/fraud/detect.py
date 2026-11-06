"""Rule baseline vs Isolation Forest on SYNTHETIC redemption events.
Run from project root: python -m ml.fraud.detect
"""
import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (precision_score, recall_score, f1_score,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import train_test_split
from ml.fraud.simulate import simulate, FEATURES

HERE = os.path.dirname(__file__)


def rule_flags(df):
    """Fixed-threshold baseline a small business might write by hand."""
    return ((df.failed_code_attempts >= 3) | (df.device_redemptions_1h >= 5) |
            (df.buyer_vouchers_24h >= 8)).astype(int).values


def isolation_forest(train_X, contamination, seed=42):
    return IsolationForest(n_estimators=200, contamination=contamination,
                           random_state=seed).fit(train_X)


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return dict(precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred), f1=f1_score(y, pred),
                false_positive_rate=fp / (fp + tn), tp=int(tp), fp=int(fp),
                fn=int(fn), tn=int(tn))


class FraudScorer:
    """Used by the Flask app on each redemption. 1 = suspicious."""

    def __init__(self, path=os.path.join(HERE, "model.joblib")):
        self.model = joblib.load(path)

    def is_suspicious(self, event: dict) -> bool:
        x = pd.DataFrame([[event[f] for f in FEATURES]], columns=FEATURES)
        return bool(self.model.predict(x)[0] == -1)

    def score(self, event: dict) -> float:
        x = pd.DataFrame([[event[f] for f in FEATURES]], columns=FEATURES)
        return float(-self.model.score_samples(x)[0])  # higher = more anomalous


def main():
    df = simulate()
    train, test = train_test_split(df, test_size=0.3, stratify=df.is_fraud, random_state=42)
    # Unsupervised: fit WITHOUT labels; contamination is an operator assumption (4%).
    model = isolation_forest(train[FEATURES], contamination=0.04)
    y = test.is_fraud.values
    pred_if = (model.predict(test[FEATURES]) == -1).astype(int)
    pred_rule = rule_flags(test)
    m_rule, m_if = metrics(y, pred_rule), metrics(y, pred_if)
    auc = roc_auc_score(y, -model.score_samples(test[FEATURES]))

    t = test.assign(rule=pred_rule, iforest=pred_if)
    subtle = t[t.pattern == "subtle"]
    blatant = t[t.pattern == "blatant"]
    lines = ["| Detector | Precision | Recall | F1 | False-positive rate |", "|---|---|---|---|---|"]
    for n, m in (("Fixed rules", m_rule), ("Isolation Forest", m_if)):
        lines.append(f"| {n} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['false_positive_rate']:.3f} |")
    lines += ["", f"Isolation Forest ROC-AUC: {auc:.3f}",
              f"Recall on blatant fraud  - rules: {blatant.rule.mean():.3f}, iforest: {blatant.iforest.mean():.3f}",
              f"Recall on subtle fraud   - rules: {subtle.rule.mean():.3f}, iforest: {subtle.iforest.mean():.3f}",
              "", "NOTE: synthetic data. Results show the method works on injected patterns, "
              "not real-world performance."]
    md = "\n".join(lines)
    print(md)
    open(os.path.join(HERE, "results.md"), "w", encoding="utf-8").write(md + "\n")

    fig, ax = plt.subplots(1, 2, figsize=(8, 3.4))
    for a, (title, p) in zip(ax, (("Fixed rules", pred_rule), ("Isolation Forest", pred_if))):
        cm = confusion_matrix(y, p)
        a.imshow(cm, cmap="Blues")
        a.set_title(title); a.set_xticks([0, 1]); a.set_yticks([0, 1])
        a.set_xticklabels(["normal", "fraud"]); a.set_yticklabels(["normal", "fraud"])
        a.set_xlabel("predicted"); a.set_ylabel("actual")
        for (i, j), v in np.ndenumerate(cm):
            a.text(j, i, v, ha="center", va="center", color="white" if v > cm.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "confusion.png"), dpi=160)

    final = isolation_forest(df[FEATURES], contamination=0.04)  # ship model trained on all
    joblib.dump(final, os.path.join(HERE, "model.joblib"))


if __name__ == "__main__":
    main()
