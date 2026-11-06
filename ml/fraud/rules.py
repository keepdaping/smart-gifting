"""Fixed-threshold fraud rules with no third-party dependencies.

Shared by the offline baseline (ml.fraud.detect.rule_flags) and by the Flask app,
which falls back to these rules when scikit-learn is not installed.
"""
RULE_THRESHOLDS = {
    "failed_code_attempts": 3,
    "device_redemptions_1h": 5,
    "buyer_vouchers_24h": 8,
}


def rule_suspicious(event):
    """True when any single signal reaches its fixed threshold."""
    return any(event[name] >= limit for name, limit in RULE_THRESHOLDS.items())


_RULE_TEXT = {
    "failed_code_attempts": "{} failed code attempts just before",
    "device_redemptions_1h": "{} vouchers for this recipient redeemed in the last hour",
    "buyer_vouchers_24h": "sender bought {} vouchers in 24 h",
}


def rule_reasons(event):
    """Plain-language list of the rules this event breaks."""
    return [_RULE_TEXT[name].format(event[name])
            for name, limit in RULE_THRESHOLDS.items() if event[name] >= limit]
