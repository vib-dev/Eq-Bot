from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..models import Event
from ..watchlists import MARKET_SYMBOL, company_name_for_symbol, match_tracked_symbol
from .base import SourceAdapter


class MoneycontrolSource(SourceAdapter):
    name = "moneycontrol"
    FEEDS = [
        "https://www.moneycontrol.com/rss/business.xml",
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
    ]

    async def fetch(self) -> list[Event]:
        events: list[Event] = []
        for feed_url in self.FEEDS:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:30]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                symbol = match_tracked_symbol(f"{title} {summary}")
                category = "news"
                company_name = company_name_for_symbol(symbol) if symbol else ""
                if not symbol and looks_like_macro(title, summary):
                    symbol = MARKET_SYMBOL
                    category = "macro"
                    company_name = "Indian Market"
                if not symbol:
                    continue
                published = _parse_time(entry.get("published_parsed"))
                events.append(
                    Event(
                        source=self.name,
                        symbol=symbol,
                        company_name=company_name,
                        title=title,
                        url=entry.get("link", ""),
                        published_at=published,
                        category=category,
                        raw_text=summary,
                    )
                )
        return events


MACRO_KEYWORDS = {
    "rbi", "sebi", "government", "ministry of finance", "budget", "inflation",
    "gdp", "repo rate", "fii", "dii", "rupee", "bond yield", "crude",
    "nifty", "sensex", "bank nifty", "trade deficit", "fiscal deficit",
    "tariff", "export", "import", "aviation ministry", "railway ministry",
}


def looks_like_macro(title: str, text: str) -> bool:
    haystack = f"{title} {text}".lower()
    return any(keyword in haystack for keyword in MACRO_KEYWORDS)


def _parse_time(parsed) -> datetime:
    if not parsed:
        return datetime.now(timezone.utc)
    return datetime(*parsed[:6], tzinfo=timezone.utc)
