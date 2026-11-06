"""Rule baseline vs Isolation Forest on SYNTHETIC redemption events.
Run from project root: python -m ml.fraud.detect
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (precision_score, recall_score, f1_score,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import train_test_split
from ml.fraud.rules import RULE_THRESHOLDS
from ml.fraud.simulate import simulate, FEATURES, REFERENCE_AMOUNT_UGX

HERE = os.path.dirname(__file__)


def rule_flags(df):
    """Fixed-threshold baseline a small business might write by hand."""
    flags = np.zeros(len(df), dtype=bool)
    for name, limit in RULE_THRESHOLDS.items():
        flags |= (df[name] >= limit).values
    return flags.astype(int)


def isolation_forest(train_X, contamination, seed=42):
    return IsolationForest(n_estimators=200, contamination=contamination,
                           random_state=seed).fit(train_X)


def metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return dict(precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred), f1=f1_score(y, pred),
                false_positive_rate=fp / (fp + tn), tp=int(tp), fp=int(fp),
                fn=int(fn), tn=int(tn))


def normalise_amount(amount_ugx, typical_amount_ugx=None):
    """Put an amount on the scale the model was trained on, relative to its merchant.

    The model learnt that ~UGX 40,000 is normal. A bakery whose cakes cost 120,000 would
    otherwise look anomalous on every sale, so amounts are expressed relative to the
    merchant's typical price and rescaled to the training reference.
    """
    if not typical_amount_ugx or typical_amount_ugx <= 0:
        return float(amount_ugx)
    return float(amount_ugx) / float(typical_amount_ugx) * REFERENCE_AMOUNT_UGX


REASONS = {
    "hours_since_purchase": "redeemed unusually soon after purchase ({:.1f} h)",
    "device_redemptions_1h": "{:.0f} vouchers for this recipient redeemed in the last hour",
    "buyer_vouchers_24h": "sender bought {:.0f} vouchers in 24 h",
    "failed_code_attempts": "{:.0f} failed code attempts just before",
    "redeem_hour": "redeemed at an unusual hour ({:02.0f}:00)",
    "amount_ugx": "value much higher than this store's usual gifts",
}


class FraudScorer:
    """Used by the Flask app on each redemption. 1 = suspicious."""

    def __init__(self, path=os.path.join(HERE, "model.joblib")):
        self.model = joblib.load(path)
        normal = simulate().query("is_fraud == 0")[FEATURES]
        self._low, self._high = normal.quantile(0.01), normal.quantile(0.99)

    def _frame(self, event):
        return pd.DataFrame([[event[f] for f in FEATURES]], columns=FEATURES)

    def is_suspicious(self, event: dict) -> bool:
        return bool(self.model.predict(self._frame(event))[0] == -1)

    def score(self, event: dict) -> float:
        return float(-self.model.score_samples(self._frame(event))[0])  # higher = more anomalous

    def reasons(self, event: dict) -> list:
        """Signals outside the 1st-99th percentile of normal (synthetic) redemptions."""
        out = []
        for name in FEATURES:
            value = event[name]
            low_is_odd = name in ("hours_since_purchase", "redeem_hour")
            if value > self._high[name] or (low_is_odd and value < self._low[name]):
                out.append(REASONS[name].format(value))
        return out

    def assess(self, event: dict, typical_amount_ugx=None) -> dict:
        """Score one redemption for any merchant. `event` holds the raw amount in UGX."""
        event = dict(event, amount_ugx=normalise_amount(event["amount_ugx"], typical_amount_ugx))
        suspicious = self.is_suspicious(event)
        return {"suspicious": suspicious, "score": round(self.score(event), 4),
                "reasons": self.reasons(event) if suspicious else [], "method": "isolation_forest"}


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

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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
