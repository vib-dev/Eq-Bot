from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote, quote_plus
from zoneinfo import ZoneInfo


def event_message(row) -> str:
    points_raw = _value(row, "key_points") or "[]"
    points = json.loads(points_raw) if isinstance(points_raw, str) else points_raw
    cmp_line = _cmp_line(row).replace("*CMP:* ", "")
    lines = [
        f"*Stock:* {_value(row, 'company_name')} ({_value(row, 'symbol')})",
        f"*CMP:* {cmp_line}",
        f"*Time:* {_display_time(_value(row, 'published_at'))}",
        "",
        f"*GIST:* {_value(row, 'summary') or _value(row, 'title')}",
    ]
    if points:
        lines.append("")
        lines.append("*KEY POINTERS:*")
        for point in points[:5]:
            lines.append(f"- {point}")
    metrics = _metrics_line(row)
    if metrics:
        lines.append("")
        lines.append(metrics)
    lines.append("")
    lines.append(f"*Source:* {str(_value(row, 'source')).upper()}")
    lines.append(f"[Official document / source]({_safe_url(_value(row, 'pdf_url') or _value(row, 'url'))})")
    lines.append(_analysis_links(row))
    return "\n".join(lines)


def help_message() -> str:
    return "\n".join(
        [
            "Available commands:",
            "/start - start tracking and load the default watchlist",
            "/help - show this command list",
            "/status - show bot health, last checks, and stored event count",
            "/watchlist - show your stocks and sectors",
            "/addstock SYMBOL - add a stock",
            "/add SYMBOL - add a stock",
            "/removestock SYMBOL - remove a stock",
            "/remove SYMBOL - remove a stock",
            "/addsector NAME - add a sector",
            "/removesector NAME - remove a sector",
            "/latest SYMBOL - latest 5 stored updates for a stock",
            "/report - top material watchlist updates since last market close",
            "/dailyreport - market-wide most important updates since last market close",
            "/morningreport - same as /dailyreport, useful for the 7 AM briefing",
            "/wake - confirm whether anything new arrived since the last alert",
            "/ask QUESTION - ask about stored announcements and news",
            "",
            "Delivery mode: GitHub Actions checks every 5 minutes and only forwards freshly published items that pass the materiality filter.",
        ]
    )


def status_message(
    *,
    now_label: str,
    last_run: str | None,
    last_sources: str | None,
    last_alerts: str | None,
    last_morning_brief: str | None,
    total_events: int,
    freshness_minutes: int,
) -> str:
    return "\n".join(
        [
            "*Bot status*",
            f"Current time: {now_label}",
            f"Last workflow run: {last_run or 'not recorded yet'}",
            f"Last source check: {last_sources or 'not recorded yet'}",
            f"Last alert cycle: {last_alerts or 'not recorded yet'}",
            f"Last 7 AM market brief: {last_morning_brief or 'not recorded yet'}",
            f"Stored events: {total_events}",
            f"Freshness window: {freshness_minutes} minutes",
            "",
            "If last workflow run is recent, the bot is working even if there are no new announcements.",
        ]
    )


def _cmp_line(row) -> str:
    if _value(row, "cmp") is None:
        return "*CMP:* unavailable"
    pct = _value(row, "pct_change")
    if pct is None:
        return f"*CMP:* {_value(row, 'cmp')}"
    return f"*CMP:* {_value(row, 'cmp')} ({pct:+.2f}% vs last close)"


def _metrics_line(row) -> str:
    parts = []
    if _value(row, "revenue"):
        parts.append(f"Revenue {_value(row, 'revenue')} ({_value(row, 'revenue_yoy') or 'YoY n/a'})")
    if _value(row, "ebitda"):
        parts.append(f"EBITDA {_value(row, 'ebitda')} ({_value(row, 'ebitda_yoy') or 'YoY n/a'})")
    if _value(row, "pat"):
        parts.append(f"PAT {_value(row, 'pat')} ({_value(row, 'pat_yoy') or 'YoY n/a'})")
    if not parts:
        return ""
    return "*Financials:* " + " | ".join(parts)


def _analysis_links(row) -> str:
    source_url = _value(row, "pdf_url") or _value(row, "url")
    query = quote_plus(
        f"Analyze this stock announcement like a financial analyst for {_value(row, 'company_name')} {_value(row, 'symbol')} {source_url}"
    )
    return f"[Google analyst search](https://www.google.com/search?q={query}) | [Open ChatGPT](https://chatgpt.com/)"


def _display_time(published_at: str) -> str:
    try:
        return datetime.fromisoformat(published_at).astimezone(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M IST")
    except Exception:
        return published_at


def _value(row, key: str):
    if hasattr(row, "keys"):
        return row[key]
    return getattr(row, key)


def _safe_url(url: str) -> str:
    return quote(url, safe=":/?&=%#.-_")
