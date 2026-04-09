from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import Settings
from .db import Database
from .models import UserProfile
from .services.ai import HeuristicSummarizer
from .services.filtering import is_fresh, materiality_score
from .services.formatting import event_message, help_message
from .services.metrics import extract_financial_metrics
from .services.quotes import QuoteService
from .services.reports import daily_digest, previous_market_close_iso, top_report
from .sources.bse import BSEAnnouncementsSource
from .sources.moneycontrol import MoneycontrolSource
from .sources.scanx import ScanXSource

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class MarketMonitorBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.db_path)
        self.summarizer = HeuristicSummarizer()
        self.quotes = QuoteService(settings.http_timeout_seconds)

    async def initialize(self) -> None:
        self.settings.ensure_paths()
        await self.db.init()

    def build_application(self) -> Application:
        if not self.settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")

        application = Application.builder().token(self.settings.telegram_bot_token).build()
        application.bot_data["service"] = self
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("watchlist", self.watchlist))
        application.add_handler(CommandHandler("addstock", self.addstock))
        application.add_handler(CommandHandler("add", self.addstock))
        application.add_handler(CommandHandler("removestock", self.removestock))
        application.add_handler(CommandHandler("remove", self.removestock))
        application.add_handler(CommandHandler("addsector", self.addsector))
        application.add_handler(CommandHandler("removesector", self.removesector))
        application.add_handler(CommandHandler("latest", self.latest))
        application.add_handler(CommandHandler("report", self.report))
        application.add_handler(CommandHandler("dailyreport", self.dailyreport))
        application.add_handler(CommandHandler("wake", self.wake))
        application.add_handler(CommandHandler("ask", self.ask))
        application.job_queue.run_repeating(
            self.poll_and_notify,
            interval=self.settings.poll_interval_minutes * 60,
            first=5,
            name="poll_and_notify",
        )
        return application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.effective_user or not update.message:
            return
        await self.db.upsert_user(
            UserProfile(
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
            )
        )
        await self.db.seed_user_defaults(update.effective_chat.id)
        await update.message.reply_text(
            "Tracking started. Your default watchlist has been loaded and the bot will poll for new updates every 5 minutes.\n\n"
            + help_message()
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(help_message())

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        stocks, sectors = await self.db.get_watchlist(update.effective_chat.id)
        text = "Stocks:\n" + ", ".join(stocks[:120]) + "\n\nSectors:\n" + ", ".join(sectors)
        await update.message.reply_text(text)

    async def addstock(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        if not context.args:
            await update.message.reply_text("Usage: /addstock SYMBOL")
            return
        await self.db.add_stock(update.effective_chat.id, context.args[0])
        await update.message.reply_text(f"Added {context.args[0].upper()} to your watchlist.")

    async def removestock(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        if not context.args:
            await update.message.reply_text("Usage: /removestock SYMBOL")
            return
        await self.db.remove_stock(update.effective_chat.id, context.args[0])
        await update.message.reply_text(f"Removed {context.args[0].upper()} from your watchlist.")

    async def addsector(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        if not context.args:
            await update.message.reply_text("Usage: /addsector sector name")
            return
        sector = " ".join(context.args)
        await self.db.add_sector(update.effective_chat.id, sector)
        await update.message.reply_text(f"Added sector: {sector}")

    async def removesector(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        if not context.args:
            await update.message.reply_text("Usage: /removesector sector name")
            return
        sector = " ".join(context.args)
        await self.db.remove_sector(update.effective_chat.id, sector)
        await update.message.reply_text(f"Removed sector: {sector}")

    async def latest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        if not context.args:
            await update.message.reply_text("Usage: /latest SYMBOL")
            return
        rows = await self.db.latest_events(context.args[0], limit=5)
        if not rows:
            await update.message.reply_text("No stored updates found for that symbol yet.")
            return
        for row in rows:
            await update.message.reply_text(
                event_message(row),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        since_iso = previous_market_close_iso(self.settings.bot_timezone)
        rows = await self.db.top_announcements_since(since_iso, limit=20)
        await update.message.reply_text(top_report(rows), parse_mode=ParseMode.MARKDOWN)

    async def dailyreport(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        day_label = datetime.now(ZoneInfo(self.settings.bot_timezone)).date().isoformat()
        rows = await self.db.daily_digest(day_label)
        await update.message.reply_text(daily_digest(rows, day_label), parse_mode=ParseMode.MARKDOWN)

    async def wake(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        since = await self.db.get_last_notified(update.effective_chat.id)
        rows = await self.db.latest_for_user(update.effective_chat.id, since_iso=since)
        if rows:
            await update.message.reply_text(f"There are {len(rows)} new stored updates since the last alert.")
        else:
            await update.message.reply_text("No new announcements or tracked news since the last bot response.")

    async def ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        question = " ".join(context.args).strip()
        if not question:
            await update.message.reply_text("Usage: /ask your question")
            return
        rows = await self.db.latest_for_user(update.effective_chat.id)
        context_lines = [f"{row['company_name']} {row['title']} {row['summary']}" for row in rows[:10]]
        answer = self.summarizer.answer(question, context_lines)
        await update.message.reply_text(answer)

    async def poll_and_notify(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        service: MarketMonitorBot = context.application.bot_data["service"]
        new_events = await service.collect_events()
        if not new_events:
            logger.info("No new events in this cycle.")
            return
        users = await service.db.get_all_users()
        for chat_id in users:
            symbols = await service.db.get_user_symbols(chat_id)
            matched = [event for event in new_events if event.symbol in symbols]
            for event in matched[: service.settings.max_updates_per_cycle]:
                rows = await service.db.latest_events(event.symbol, limit=1)
                if not rows:
                    continue
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=event_message(rows[0]),
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
                await service.db.set_last_notified(chat_id, event.published_at.isoformat())

    async def collect_events(self) -> list:
        adapters = []
        if self.settings.enable_bse:
            adapters.append(BSEAnnouncementsSource())
        if self.settings.enable_moneycontrol:
            adapters.append(MoneycontrolSource())
        if self.settings.enable_scanx:
            adapters.append(ScanXSource())

        new_events = []
        for adapter in adapters:
            try:
                events = await adapter.fetch()
                logger.info("Fetched %s events from %s", len(events), adapter.name)
            except Exception as exc:
                logger.exception("Source adapter failed: %s", adapter.name, exc_info=exc)
                continue
            for event in events:
                if not is_fresh(event.published_at, self.settings.real_time_freshness_minutes):
                    logger.info(
                        "Skipping stale event from %s for %s at %s",
                        adapter.name,
                        event.symbol,
                        event.published_at.isoformat(),
                    )
                    continue
                event.materiality_score = materiality_score(event.title, event.raw_text)
                if event.materiality_score <= 0:
                    continue
                event.summary, event.key_points = self.summarizer.summarize(event.title, event.raw_text)
                metrics = extract_financial_metrics(event.raw_text)
                event.revenue = metrics["revenue"]
                event.revenue_yoy = metrics["revenue_yoy"]
                event.ebitda = metrics["ebitda"]
                event.ebitda_yoy = metrics["ebitda_yoy"]
                event.pat = metrics["pat"]
                event.pat_yoy = metrics["pat_yoy"]
                event.cmp, event.pct_change = await self.quotes.fetch_quote(event.symbol)
                inserted = await self.db.insert_event(event)
                if inserted:
                    new_events.append(event)
        return sorted(new_events, key=lambda item: item.published_at, reverse=True)


def main() -> None:
    settings = Settings.from_env()
    service = MarketMonitorBot(settings)
    asyncio.run(service.initialize())
    app = service.build_application()
    app.run_polling(drop_pending_updates=True)
