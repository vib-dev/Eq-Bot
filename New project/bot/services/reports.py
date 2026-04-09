from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def previous_market_close_iso(tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now <= close:
        close = close - timedelta(days=1)
    while close.weekday() >= 5:
        close = close - timedelta(days=1)
    return close.isoformat()


def top_report(rows) -> str:
    if not rows:
        return "No material announcements found since the last market close."
    lines = ["*Top corporate announcements since last market close:*"]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"{idx}. {row['company_name']} ({row['symbol']}): {row['summary'] or row['title']}")
    return "\n".join(lines)


def daily_digest(rows, day_label: str) -> str:
    if not rows:
        return f"No stored announcement digest for {day_label}."
    lines = [f"*Daily announcements digest for {day_label}:*"]
    for row in rows[:40]:
        lines.append(f"- {row['company_name']} ({row['symbol']}): {row['summary'] or row['title']}")
    return "\n".join(lines)
