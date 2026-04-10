from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from ..models import Event
from ..watchlists import company_name_for_symbol, match_tracked_symbol, normalize_company_key
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

        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            company = " ".join(cells[0].get_text(" ", strip=True).split())
            filing_category = " ".join(cells[1].get_text(" ", strip=True).split())
            description = " ".join(cells[2].get_text(" ", strip=True).split())
            reported_time = " ".join(cells[3].get_text(" ", strip=True).split())
            published_at = _parse_reported_time(reported_time)
            document_anchor = cells[4].find("a", href=True)
            if not company or not description or not published_at or not document_anchor:
                continue
            href = document_anchor.get("href", "")
            if not href:
                continue
            link = href if href.startswith("http") else f"https://scanx.trade{href}"
            matched_symbol = match_tracked_symbol(f"{company} {description}")
            symbol = matched_symbol or normalize_company_key(company)
            events.append(
                Event(
                    source=self.name,
                    symbol=symbol,
                    company_name=company_name_for_symbol(matched_symbol) if matched_symbol else company,
                    title=f"{company}: {description}",
                    url=link,
                    pdf_url=link,
                    published_at=published_at,
                    category="announcement",
                    raw_text=f"{filing_category}. {description}",
                    tags=[filing_category] if filing_category else [],
                )
            )
        return events


def _parse_reported_time(value: str) -> datetime | None:
    text = value.strip().lower()
    now = datetime.now(timezone.utc)
    minute_match = re.search(r"(\d+)\s*min", text)
    if minute_match:
        return now - timedelta(minutes=int(minute_match.group(1)))
    hour_match = re.search(r"(\d+)\s*hr", text)
    if hour_match:
        return now - timedelta(hours=int(hour_match.group(1)))
    day_match = re.search(r"(\d+)\s*day", text)
    if day_match:
        return now - timedelta(days=int(day_match.group(1)))
    absolute_match = re.search(r"(\d{1,2})[-/ ]([A-Za-z]{3})[-/ ](\d{4})", value)
    if absolute_match:
        try:
            return datetime.strptime(absolute_match.group(0), "%d %b %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None
