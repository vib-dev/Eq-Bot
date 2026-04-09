from __future__ import annotations

import json


def event_message(row) -> str:
    points = json.loads(row["key_points"] or "[]")
    cmp_line = _cmp_line(row).replace("*CMP:* ", "")
    lines = [
        f"*Stock:* {row['company_name']} ({row['symbol']})",
        f"*CMP:* {cmp_line}",
        "",
        f"*GIST:* {row['summary'] or row['title']}",
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
    lines.append(f"*Source:* {row['source'].upper()}")
    lines.append(f"[PDF / source link]({row['pdf_url'] or row['url']})")
    return "\n".join(lines)


def help_message() -> str:
    return "\n".join(
        [
            "Available commands:",
            "/start - start tracking and load the default watchlist",
            "/help - show this command list",
            "/watchlist - show your stocks and sectors",
            "/addstock SYMBOL - add a stock",
            "/removestock SYMBOL - remove a stock",
            "/addsector NAME - add a sector",
            "/removesector NAME - remove a sector",
            "/latest SYMBOL - latest 5 stored updates for a stock",
            "/report - top material announcements since last market close",
            "/dailyreport - daily consolidated announcements digest",
            "/wake - confirm whether anything new arrived since the last alert",
            "/ask QUESTION - ask about stored announcements and news",
            "",
            "Delivery mode: GitHub Actions checks every 5 minutes and only forwards freshly published items that pass the materiality filter.",
        ]
    )


def _cmp_line(row) -> str:
    if row["cmp"] is None:
        return "*CMP:* unavailable"
    pct = row["pct_change"]
    if pct is None:
        return f"*CMP:* {row['cmp']}"
    return f"*CMP:* {row['cmp']} ({pct:+.2f}% vs last close)"


def _metrics_line(row) -> str:
    parts = []
    if row["revenue"]:
        parts.append(f"Revenue {row['revenue']} ({row['revenue_yoy'] or 'YoY n/a'})")
    if row["ebitda"]:
        parts.append(f"EBITDA {row['ebitda']} ({row['ebitda_yoy'] or 'YoY n/a'})")
    if row["pat"]:
        parts.append(f"PAT {row['pat']} ({row['pat_yoy'] or 'YoY n/a'})")
    if not parts:
        return ""
    return "*Financials:* " + " | ".join(parts)
