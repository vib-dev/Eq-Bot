from __future__ import annotations

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from ..models import Event
from ..watchlists import canonical_symbol
from .base import SourceAdapter


class ScanXSource(SourceAdapter):
    name = "scanx"
    URL = "https://scanx.trade/insight/company-filings"

    async def fetch(self) -> list[Event]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.URL, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        events: list[Event] = []

        for anchor in soup.select("a[href*='/company/'], a[href*='/insight/']")[:80]:
            text = " ".join(anchor.get_text(" ", strip=True).split())
            href = anchor.get("href", "")
            symbol = _extract_symbol(text)
            if not text or not href or not symbol:
                continue
            link = href if href.startswith("http") else f"https://scanx.trade{href}"
            events.append(
                Event(
                    source=self.name,
                    symbol=symbol,
                    company_name=symbol,
                    title=text,
                    url=link,
                    published_at=datetime.now(timezone.utc),
                    category="announcement",
                    raw_text=text,
                )
            )
        return events


def _extract_symbol(text: str) -> str | None:
    for token in text.upper().replace(",", " ").split():
        cleaned = token.strip("():.- ")
        if cleaned.isalpha() and 2 <= len(cleaned) <= 12:
            return canonical_symbol(cleaned)
    return None
