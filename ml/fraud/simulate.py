"""SYNTHETIC voucher-redemption events with injected fraud patterns.
No real customer data is used. Run: python -m ml.fraud.simulate
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
FEATURES = ["hours_since_purchase", "device_redemptions_1h", "buyer_vouchers_24h",
            "failed_code_attempts", "redeem_hour", "amount_ugx"]
NORMAL_AMOUNT_LOG_MEAN = 10.6
# Median amount of a normal synthetic redemption (about UGX 40,000). Live amounts are
# rescaled to this level per merchant before scoring; see detect.normalise_amount.
REFERENCE_AMOUNT_UGX = float(np.exp(NORMAL_AMOUNT_LOG_MEAN))


def simulate(n=6000, fraud_rate=0.04, seed=42):
    rng = np.random.default_rng(seed)
    n_f = int(n * fraud_rate)
    n_n = n - n_f
    normal = pd.DataFrame({
        "hours_since_purchase": rng.gamma(2.0, 18.0, n_n) + 0.5,
        "device_redemptions_1h": rng.poisson(0.3, n_n),
        "buyer_vouchers_24h": rng.poisson(1.2, n_n) + 1,
        "failed_code_attempts": rng.poisson(0.15, n_n),
        "redeem_hour": np.clip(rng.normal(13, 3.5, n_n), 6, 23).astype(int),
        "amount_ugx": rng.lognormal(NORMAL_AMOUNT_LOG_MEAN, 0.6, n_n).round(-2),
        "is_fraud": 0, "pattern": "normal"})
    nb = n_f // 2            # blatant fraud: extreme on several signals
    ns = n_f - nb            # subtle fraud: only moderately unusual on several signals
    blatant = pd.DataFrame({
        "hours_since_purchase": rng.uniform(0.01, 0.5, nb),
        "device_redemptions_1h": rng.poisson(6, nb) + 4,
        "buyer_vouchers_24h": rng.poisson(8, nb) + 6,
        "failed_code_attempts": rng.poisson(5, nb) + 3,
        "redeem_hour": rng.integers(0, 5, nb),
        "amount_ugx": rng.lognormal(11.4, 0.5, nb).round(-2),
        "is_fraud": 1, "pattern": "blatant"})
    subtle = pd.DataFrame({
        "hours_since_purchase": rng.uniform(0.2, 3.0, ns),
        "device_redemptions_1h": rng.poisson(1.5, ns) + 1,
        "buyer_vouchers_24h": rng.poisson(3, ns) + 3,
        "failed_code_attempts": rng.poisson(1.2, ns) + 1,
        "redeem_hour": rng.choice([0, 1, 2, 3, 4, 5, 22, 23], ns),
        "amount_ugx": rng.lognormal(11.0, 0.5, ns).round(-2),
        "is_fraud": 1, "pattern": "subtle"})
    df = pd.concat([normal, blatant, subtle], ignore_index=True)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


if __name__ == "__main__":
    df = simulate()
    path = os.path.join(HERE, "synthetic_transactions.csv")
    df.to_csv(path, index=False)
    print(f"wrote {path}: {len(df)} rows, {int(df.is_fraud.sum())} fraud (SYNTHETIC)")
