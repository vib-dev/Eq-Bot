from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..models import Event
from ..watchlists import canonical_symbol
from .base import SourceAdapter


class BSEAnnouncementsSource(SourceAdapter):
    name = "bse"
    FEED_URL = "https://www.bseindia.com/rss/ann.xml"

    async def fetch(self) -> list[Event]:
        parsed = feedparser.parse(self.FEED_URL)
        events: list[Event] = []
        for entry in parsed.entries[:50]:
            title = entry.get("title", "").strip()
            symbol = _extract_symbol(title)
            if not symbol:
                continue
            published = _parse_time(entry.get("published_parsed"))
            link = entry.get("link", "")
            events.append(
                Event(
                    source=self.name,
                    symbol=symbol,
                    company_name=symbol,
                    title=title,
                    url=link,
                    pdf_url=link,
                    published_at=published,
                    category="announcement",
                    raw_text=entry.get("summary", ""),
                    exchange="BSE",
                )
            )
        return events


def _extract_symbol(title: str) -> str | None:
    for part in title.replace("-", " ").split():
        token = part.strip("():, ")
        if token.isalpha() and 2 <= len(token) <= 12:
            return canonical_symbol(token)
    return None


def _parse_time(parsed) -> datetime:
    if not parsed:
        return datetime.now(timezone.utc)
    return datetime(*parsed[:6], tzinfo=timezone.utc)

