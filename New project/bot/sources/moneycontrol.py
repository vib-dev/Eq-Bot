from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..models import Event
from ..watchlists import canonical_symbol
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
                symbol = extract_symbol(title, summary)
                if not symbol:
                    continue
                published = _parse_time(entry.get("published_parsed"))
                events.append(
                    Event(
                        source=self.name,
                        symbol=symbol,
                        company_name=symbol,
                        title=title,
                        url=entry.get("link", ""),
                        published_at=published,
                        category="news",
                        raw_text=summary,
                    )
                )
        return events


def extract_symbol(title: str, text: str) -> str | None:
    haystack = f"{title} {text}".upper()
    for token in haystack.replace(",", " ").split():
        compact = token.strip("():.- ")
        if compact.isalpha() and 2 <= len(compact) <= 12:
            return canonical_symbol(compact)
    return None


def _parse_time(parsed) -> datetime:
    if not parsed:
        return datetime.now(timezone.utc)
    return datetime(*parsed[:6], tzinfo=timezone.utc)

