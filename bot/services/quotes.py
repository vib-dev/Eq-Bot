from __future__ import annotations

import httpx


class QuoteService:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_quote(self, symbol: str) -> tuple[float | None, float | None]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                payload = response.json()
                result = payload["chart"]["result"][0]["meta"]
                price = result.get("regularMarketPrice")
                previous = result.get("chartPreviousClose") or result.get("previousClose")
                if price is None or previous in (None, 0):
                    return None, None
                pct_change = ((price - previous) / previous) * 100
                return float(price), round(float(pct_change), 2)
        except Exception:
            return None, None

