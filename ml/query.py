"""Pulls a budget (UGX) out of a natural-language gift request."""
import re

_CUE = re.compile(r"\b(under|below|less than|within|up ?to|budget|max(?:imum)?|ugx|shs?)\b|<", re.I)
_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(k)?\b", re.I)


def parse_budget(query):
    has_cue = bool(_CUE.search(query))
    found = []
    for m in _NUM.finditer(query):
        v = float(m.group(1).replace(",", ""))
        if m.group(2):
            v *= 1000
        elif not has_cue:
            continue
        if v >= 1000:
            found.append(int(v))
    return min(found) if found else None


def clean_query(query):
    q = _NUM.sub(" ", query)
    q = _CUE.sub(" ", q)
    return re.sub(r"\s+", " ", q).strip()
