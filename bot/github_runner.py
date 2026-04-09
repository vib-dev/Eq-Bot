from __future__ import annotations

import asyncio
import logging
import shlex
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Settings
from .main import MarketMonitorBot
from .services.formatting import event_message
from .services.reports import daily_digest, previous_market_close_iso, top_report
from .telegram_api import TelegramApi

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class GitHubActionsRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.service = MarketMonitorBot(settings)
        self.telegram = TelegramApi(settings.telegram_bot_token, settings.http_timeout_seconds)

    async def run_once(self) -> None:
        await self.service.initialize()
        await self.process_updates()
        await self.push_new_events()

    async def process_updates(self) -> None:
        offset = await self.service.db.get_telegram_offset()
        logger.info("Fetching Telegram updates with offset=%s", offset)
        updates = await self.telegram.get_updates(offset=offset)
        logger.info("Received %s Telegram updates", len(updates))
        if not updates:
            return
        max_update_id = offset or 0
        for update in updates:
            max_update_id = max(max_update_id, update["update_id"] + 1)
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            chat = message.get("chat") or {}
            user = message.get("from") or {}
            chat_id = chat.get("id")
            if not chat_id or not text.startswith("/"):
                continue
            logger.info("Processing command %s for chat_id=%s", text, chat_id)
            await self.service.db.upsert_telegram_user(chat_id, user.get("username"), user.get("first_name"))
            await self.handle_command(chat_id, text)
        await self.service.db.set_telegram_offset(max_update_id)

    async def handle_command(self, chat_id: int, text: str) -> None:
        parts = shlex.split(text)
        command = parts[0].split("@")[0].lower()
        args = parts[1:]

        if command == "/start":
            await self.service.db.seed_user_defaults(chat_id)
            await self.telegram.send_message(chat_id, "Tracking started. Default watchlist loaded.")
            return
        if command == "/watchlist":
            stocks, sectors = await self.service.db.get_watchlist(chat_id)
            await self.telegram.send_message(chat_id, "Stocks:\n" + ", ".join(stocks) + "\n\nSectors:\n" + ", ".join(sectors))
            return
        if command == "/addstock" and args:
            await self.service.db.add_stock(chat_id, args[0])
            await self.telegram.send_message(chat_id, f"Added {args[0].upper()} to your watchlist.")
            return
        if command == "/removestock" and args:
            await self.service.db.remove_stock(chat_id, args[0])
            await self.telegram.send_message(chat_id, f"Removed {args[0].upper()} from your watchlist.")
            return
        if command == "/addsector" and args:
            sector = " ".join(args)
            await self.service.db.add_sector(chat_id, sector)
            await self.telegram.send_message(chat_id, f"Added sector: {sector}")
            return
        if command == "/removesector" and args:
            sector = " ".join(args)
            await self.service.db.remove_sector(chat_id, sector)
            await self.telegram.send_message(chat_id, f"Removed sector: {sector}")
            return
        if command == "/latest" and args:
            rows = await self.service.db.latest_events(args[0], limit=5)
            if not rows:
                await self.telegram.send_message(chat_id, "No stored updates found for that symbol yet.")
                return
            for row in rows:
                await self.telegram.send_message(chat_id, event_message(row))
            return
        if command == "/report":
            since_iso = previous_market_close_iso(self.settings.bot_timezone)
            rows = await self.service.db.top_announcements_since(since_iso, limit=20)
            await self.telegram.send_message(chat_id, top_report(rows))
            return
        if command == "/dailyreport":
            day_label = datetime.now(ZoneInfo(self.settings.bot_timezone)).date().isoformat()
            rows = await self.service.db.daily_digest(day_label)
            await self.telegram.send_message(chat_id, daily_digest(rows, day_label))
            return
        if command == "/wake":
            since = await self.service.db.get_last_notified(chat_id)
            rows = await self.service.db.latest_for_user(chat_id, since_iso=since)
            if rows:
                await self.telegram.send_message(chat_id, f"There are {len(rows)} new stored updates since the last alert.")
            else:
                await self.telegram.send_message(chat_id, "No new announcements or tracked news since the last bot response.")
            return
        if command == "/ask" and args:
            rows = await self.service.db.latest_for_user(chat_id)
            context_lines = [f"{row['company_name']} {row['title']} {row['summary']}" for row in rows[:10]]
            answer = self.service.summarizer.answer(" ".join(args), context_lines)
            await self.telegram.send_message(chat_id, answer)
            return
        await self.telegram.send_message(chat_id, "Unknown command or missing argument.")

    async def push_new_events(self) -> None:
        new_events = await self.service.collect_events()
        if not new_events:
            logger.info("No new events in this cycle.")
            return
        users = await self.service.db.get_all_users()
        for chat_id in users:
            symbols = await self.service.db.get_user_symbols(chat_id)
            matched = [event for event in new_events if event.symbol in symbols]
            for event in matched[: self.settings.max_updates_per_cycle]:
                rows = await self.service.db.latest_events(event.symbol, limit=1)
                if not rows:
                    continue
                await self.telegram.send_message(chat_id, event_message(rows[0]))
                await self.service.db.set_last_notified(chat_id, event.published_at.isoformat())


def main() -> None:
    settings = Settings.from_env()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
    runner = GitHubActionsRunner(settings)
    asyncio.run(runner.run_once())


if __name__ == "__main__":
    main()
