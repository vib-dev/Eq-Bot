from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..models import Event
from ..watchlists import company_name_for_symbol, match_tracked_symbol
from .base import SourceAdapter


class BSEAnnouncementsSource(SourceAdapter):
    name = "bse"
    FEED_URL = "https://www.bseindia.com/rss/ann.xml"

    async def fetch(self) -> list[Event]:
        parsed = feedparser.parse(self.FEED_URL)
        events: list[Event] = []
        for entry in parsed.entries[:50]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "")
            symbol = match_tracked_symbol(f"{title} {summary}")
            if not symbol:
                continue
            published = _parse_time(entry.get("published_parsed"))
            link = entry.get("link", "")
            events.append(
                Event(
                    source=self.name,
                    symbol=symbol,
                    company_name=company_name_for_symbol(symbol),
                    title=title,
                    url=link,
                    pdf_url=link,
                    published_at=published,
                    category="announcement",
                    raw_text=summary,
                    exchange="BSE",
                )
            )
        return events


def _parse_time(parsed) -> datetime:
    if not parsed:
        return datetime.now(timezone.utc)
    return datetime(*parsed[:6], tzinfo=timezone.utc)
