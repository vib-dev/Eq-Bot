from __future__ import annotations

import asyncio
import logging
import shlex
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Settings
from .main import MarketMonitorBot
from .services.formatting import event_message, help_message, status_message
from .services.reports import daily_digest, morning_market_brief, previous_market_close_iso, top_report
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
        await self.send_morning_briefing_if_due()

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
            await self.telegram.send_message(chat_id, "Tracking started. Default watchlist loaded.\n\n" + help_message())
            await self.telegram.send_message(chat_id, await self.build_status_text())
            return
        if command == "/help":
            await self.telegram.send_message(chat_id, help_message())
            await self.telegram.send_message(chat_id, await self.build_status_text())
            return
        if command == "/status":
            await self.telegram.send_message(chat_id, await self.build_status_text())
            return
        if command == "/watchlist":
            stocks, sectors = await self.service.db.get_watchlist(chat_id)
            await self.telegram.send_message(chat_id, "Stocks:\n" + ", ".join(stocks) + "\n\nSectors:\n" + ", ".join(sectors))
            return
        if command == "/addstock" and args:
            await self.service.db.add_stock(chat_id, args[0])
            await self.telegram.send_message(chat_id, f"Added {args[0].upper()} to your watchlist.")
            return
        if command == "/add" and args:
            await self.service.db.add_stock(chat_id, args[0])
            await self.telegram.send_message(chat_id, f"Added {args[0].upper()} to your watchlist.")
            return
        if command == "/removestock" and args:
            await self.service.db.remove_stock(chat_id, args[0])
            await self.telegram.send_message(chat_id, f"Removed {args[0].upper()} from your watchlist.")
            return
        if command == "/remove" and args:
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
            await self.refresh_live_data()
            rows = await self.service.db.ranked_latest_events(args[0], limit=5)
            if not rows:
                await self.telegram.send_message(chat_id, "No stored updates found for that symbol yet.")
                return
            for row in rows:
                await self.telegram.send_message(chat_id, event_message(row))
            return
        if command == "/report":
            await self.refresh_live_data()
            since_iso = previous_market_close_iso(self.settings.bot_timezone)
            rows = await self.service.db.top_for_user_since(chat_id, since_iso, limit=20)
            await self.telegram.send_message(chat_id, top_report(rows))
            return
        if command in {"/dailyreport", "/morningreport"}:
            await self.refresh_live_data()
            since_iso = previous_market_close_iso(self.settings.bot_timezone)
            rows = await self.service.db.market_briefing_since(since_iso, limit=25)
            await self.telegram.send_message(chat_id, morning_market_brief(rows, tz_name=self.settings.bot_timezone))
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

    async def refresh_live_data(self) -> None:
        last_refresh = await self.service.db.get_meta("last_manual_refresh")
        now = datetime.now(ZoneInfo(self.settings.bot_timezone))
        if last_refresh == now.strftime("%Y-%m-%d-%H-%M"):
            return
        await self.service.collect_events()
        await self.service.db.set_meta("last_manual_refresh", now.strftime("%Y-%m-%d-%H-%M"))
        await self.service.db.set_meta("last_source_check", now.isoformat())

    async def push_new_events(self) -> None:
        now = datetime.now(ZoneInfo(self.settings.bot_timezone))
        await self.service.db.set_meta("last_workflow_run", now.isoformat())
        new_events = await self.service.collect_events()
        await self.service.db.set_meta("last_source_check", now.isoformat())
        if not new_events:
            logger.info("No new events in this cycle.")
            await self.send_heartbeat(had_updates=False)
            return
        users = await self.service.db.get_all_users()
        for chat_id in users:
            symbols = await self.service.db.get_user_symbols(chat_id)
            matched = [event for event in new_events if event.symbol in symbols]
            for event in matched[: self.settings.max_updates_per_cycle]:
                await self.telegram.send_message(chat_id, event_message(event))
                await self.service.db.set_last_notified(chat_id, event.published_at.isoformat())
        await self.service.db.set_meta("last_alert_cycle", now.isoformat())
        await self.send_heartbeat(had_updates=True)

    async def send_morning_briefing_if_due(self) -> None:
        now = datetime.now(ZoneInfo(self.settings.bot_timezone))
        if now.hour != 7 or now.minute >= 10:
            return
        day_key = now.strftime("%Y-%m-%d")
        sent_day = await self.service.db.get_meta("last_morning_brief_day")
        if sent_day == day_key:
            return
        since_iso = previous_market_close_iso(self.settings.bot_timezone)
        rows = await self.service.db.market_briefing_since(since_iso, limit=25)
        message = morning_market_brief(rows, tz_name=self.settings.bot_timezone)
        users = await self.service.db.get_all_users()
        for chat_id in users:
            await self.telegram.send_message(chat_id, message)
        await self.service.db.set_meta("last_morning_brief_day", day_key)
        await self.service.db.set_meta("last_morning_brief_at", now.isoformat())

    async def send_heartbeat(self, had_updates: bool) -> None:
        if not self.settings.enable_heartbeat:
            return
        now = datetime.now(ZoneInfo(self.settings.bot_timezone))
        hour_key = now.strftime("%Y-%m-%d-%H")
        users = await self.service.db.get_all_users()
        for chat_id in users:
            meta_key = f"heartbeat:{chat_id}"
            last_hour = await self.service.db.get_meta(meta_key)
            if last_hour == hour_key:
                continue
            status = "New matched updates were processed in the latest hour." if had_updates else "No new tracked updates in the latest cycle."
            await self.telegram.send_message(
                chat_id,
                f"Heartbeat: bot is running normally as of {now.strftime('%Y-%m-%d %H:%M %Z')}. {status}"
            )
            await self.service.db.set_meta(meta_key, hour_key)

    async def build_status_text(self) -> str:
        now = datetime.now(ZoneInfo(self.settings.bot_timezone))
        total_events = await self.service.db.count_events()
        return status_message(
            now_label=now.strftime("%Y-%m-%d %H:%M %Z"),
            last_run=await self.service.db.get_meta("last_workflow_run"),
            last_sources=await self.service.db.get_meta("last_source_check"),
            last_alerts=await self.service.db.get_meta("last_alert_cycle"),
            last_morning_brief=await self.service.db.get_meta("last_morning_brief_at"),
            total_events=total_events,
            freshness_minutes=self.settings.real_time_freshness_minutes,
        )


def main() -> None:
    settings = Settings.from_env()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
    runner = GitHubActionsRunner(settings)
    asyncio.run(runner.run_once())


if __name__ == "__main__":
    main()
