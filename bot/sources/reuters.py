from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..models import Event
from ..watchlists import DEFAULT_WATCHLIST, canonical_symbol
from .base import SourceAdapter


class ReutersSource(SourceAdapter):
    name = "reuters"

    async def fetch(self) -> list[Event]:
        events: list[Event] = []
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for symbol in DEFAULT_WATCHLIST[:15]:
                url = f"https://www.reuters.com/site-search/?query={quote_plus(symbol)}"
                try:
                    response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    response.raise_for_status()
                except Exception:
                    continue
                soup = BeautifulSoup(response.text, "lxml")
                for anchor in soup.select("a[href*='/world/'], a[href*='/markets/'], a[href*='/business/']")[:2]:
                    title = " ".join(anchor.get_text(" ", strip=True).split())
                    href = anchor.get("href", "")
                    if not title or not href:
                        continue
                    link = href if href.startswith("http") else f"https://www.reuters.com{href}"
                    events.append(
                        Event(
                            source=self.name,
                            symbol=canonical_symbol(symbol),
                            company_name=canonical_symbol(symbol),
                            title=title,
                            url=link,
                            published_at=datetime.now(timezone.utc),
                            category="news",
                        )
                    )
        return events
