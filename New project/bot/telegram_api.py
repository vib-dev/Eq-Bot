from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramApi:
    def __init__(self, token: str, timeout_seconds: int = 20) -> None:
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout_seconds = timeout_seconds

    async def get_updates(self, offset: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"limit": limit, "timeout": 0}
        if offset is not None:
            payload["offset"] = offset
        result = await self._request("getUpdates", payload)
        return result or []

    async def send_message(self, chat_id: int, text: str) -> None:
        await self._request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        )

    async def _request(self, method: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.post(f"{self.base_url}/{method}", json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                logger.warning("Telegram API error on %s: %s", method, data)
                return None
            return data.get("result")

