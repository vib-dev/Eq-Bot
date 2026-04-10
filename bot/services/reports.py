from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..watchlists import RESEARCH_UNIVERSE


def previous_market_close_iso(tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now <= close:
        close = close - timedelta(days=1)
    while close.weekday() >= 5:
        close = close - timedelta(days=1)
    return close.isoformat()


def previous_market_close_label(tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    return datetime.fromisoformat(previous_market_close_iso(tz_name)).astimezone(tz).strftime("%Y-%m-%d %H:%M %Z")


def top_report(rows) -> str:
    if not rows:
        return "No material announcements found since the last market close."
    lines = ["*Top material updates since last market close:*"]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"{idx}. {_company_label(row)} | {_row_time(row)} | {row['summary'] or row['title']}")
    return "\n".join(lines)


def daily_digest(rows, day_label: str) -> str:
    if not rows:
        return f"No stored announcement digest for {day_label}."
    lines = [f"*Most important announcements for {day_label}:*"]
    for row in rows[:40]:
        lines.append(f"- {_company_label(row)} | {_row_time(row)} | {row['summary'] or row['title']}")
    return "\n".join(lines)


def morning_market_brief(rows, *, tz_name: str) -> str:
    since_label = previous_market_close_label(tz_name)
    if not rows:
        return f"*7 AM Market Brief*\nNo material market-wide updates were stored since last close ({since_label})."

    macro_rows = [row for row in rows if row["category"] == "macro"]
    company_rows = [row for row in rows if row["category"] != "macro"]

    lines = [f"*7 AM Market Brief*", f"Coverage window: since last close ({since_label})", ""]

    if macro_rows:
        lines.append("*Macro / Market-wide:*")
        for row in macro_rows[:6]:
            lines.append(f"- {_row_time(row)} | {row['summary'] or row['title']}")
        lines.append("")

    if company_rows:
        lines.append("*Top company-specific updates:*")
        for idx, row in enumerate(company_rows[:15], start=1):
            lines.append(f"{idx}. {_company_label(row)} | {_row_time(row)} | {row['summary'] or row['title']}")

    return "\n".join(lines)


def _row_time(row) -> str:
    try:
        return datetime.fromisoformat(row["published_at"]).astimezone(ZoneInfo("Asia/Kolkata")).strftime("%H:%M IST")
    except Exception:
        return "time n/a"


def _company_label(row) -> str:
    symbol = row["symbol"]
    company_name = row["company_name"]
    if symbol in RESEARCH_UNIVERSE:
        return f"{company_name} ({symbol})"
    return company_name
