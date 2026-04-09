from __future__ import annotations

IMMATERIAL_TERMS = {
    "esop", "dividend", "minor penalty", "fine", "trading window",
    "loss of share certificate", "duplicate certificate", "newspaper advertisement",
}

MATERIAL_TERMS = {
    "results", "board meeting", "acquisition", "merger", "fund raising",
    "order win", "contract", "capex", "expansion", "guidance", "traffic",
    "default", "rating", "buyback", "bonus", "split", "stake sale",
    "strategic partnership", "plant", "capacity", "q1", "q2", "q3", "q4",
}


def materiality_score(title: str, text: str, market_cap_crore: float | None = None) -> int:
    haystack = f"{title} {text}".lower()
    if market_cap_crore is not None and market_cap_crore < 1000:
        return 0
    if any(term in haystack for term in IMMATERIAL_TERMS):
        return 0
    score = 1
    for term in MATERIAL_TERMS:
        if term in haystack:
            score += 2
    if any(word in haystack for word in ("revenue", "ebitda", "pat", "profit", "loss")):
        score += 3
    return min(score, 10)

