from __future__ import annotations

import re


def extract_financial_metrics(text: str) -> dict[str, str | None]:
    lowered = " ".join(text.split())
    return {
        "revenue": _find_metric(lowered, r"(revenue|income from operations)[^.\n]{0,80}?₹?\s?([\d,]+(?:\.\d+)?)\s?(crore|cr|mn|bn)?"),
        "revenue_yoy": _find_change(lowered, "revenue"),
        "ebitda": _find_metric(lowered, r"(ebitda)[^.\n]{0,80}?₹?\s?([\d,]+(?:\.\d+)?)\s?(crore|cr|mn|bn)?"),
        "ebitda_yoy": _find_change(lowered, "ebitda"),
        "pat": _find_metric(lowered, r"(pat|profit after tax|net profit)[^.\n]{0,80}?₹?\s?([\d,]+(?:\.\d+)?)\s?(crore|cr|mn|bn)?"),
        "pat_yoy": _find_change(lowered, "pat"),
    }


def _find_metric(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    unit = f" {match.group(3)}" if match.group(3) else ""
    return f"{match.group(2)}{unit}".strip()


def _find_change(text: str, label: str) -> str | None:
    pattern = rf"{label}[^.\n]{{0,100}}?((?:up|down|rise|fall|increase|decrease|grew|declined)[^.\n]{{0,20}}?\d+(?:\.\d+)?%)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else None

