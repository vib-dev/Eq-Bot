from __future__ import annotations

import json


def event_message(row) -> str:
    points = json.loads(row["key_points"] or "[]")
    lines = [
        f"*{row['company_name']} ({row['symbol']})*",
        _cmp_line(row),
        f"*Gist:* {row['summary'] or row['title']}",
    ]
    if points:
        lines.append("*Key pointers:*")
        for point in points[:5]:
            lines.append(f"- {point}")
    metrics = _metrics_line(row)
    if metrics:
        lines.append(metrics)
    lines.append(f"[PDF / source link]({row['pdf_url'] or row['url']})")
    return "\n".join(lines)


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

