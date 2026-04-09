from __future__ import annotations

import json

import aiosqlite

from .models import Event, UserProfile
from .watchlists import DEFAULT_SECTORS, DEFAULT_WATCHLIST, canonical_symbol


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_notified_at TEXT
);

CREATE TABLE IF NOT EXISTS watchlist_stocks (
    chat_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, symbol)
);

CREATE TABLE IF NOT EXISTS watchlist_sectors (
    chat_id INTEGER NOT NULL,
    sector TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, sector)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    pdf_url TEXT,
    published_at TEXT NOT NULL,
    category TEXT NOT NULL,
    raw_text TEXT,
    exchange TEXT,
    cmp REAL,
    pct_change REAL,
    revenue TEXT,
    revenue_yoy TEXT,
    ebitda TEXT,
    ebitda_yoy TEXT,
    pat TEXT,
    pat_yoy TEXT,
    materiality_score INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '[]',
    summary TEXT,
    key_points TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, symbol, title, published_at, url)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def upsert_user(self, profile: UserProfile) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users(chat_id, username, first_name)
                VALUES(?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
                """,
                (profile.chat_id, profile.username, profile.first_name),
            )
            await db.commit()

    async def upsert_telegram_user(self, chat_id: int, username: str | None, first_name: str | None) -> None:
        await self.upsert_user(UserProfile(chat_id=chat_id, username=username, first_name=first_name))

    async def seed_user_defaults(self, chat_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            for symbol in DEFAULT_WATCHLIST:
                await db.execute(
                    "INSERT OR IGNORE INTO watchlist_stocks(chat_id, symbol) VALUES(?, ?)",
                    (chat_id, canonical_symbol(symbol)),
                )
            for sector in DEFAULT_SECTORS:
                await db.execute(
                    "INSERT OR IGNORE INTO watchlist_sectors(chat_id, sector) VALUES(?, ?)",
                    (chat_id, sector),
                )
            await db.commit()

    async def add_stock(self, chat_id: int, symbol: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO watchlist_stocks(chat_id, symbol) VALUES(?, ?)",
                (chat_id, canonical_symbol(symbol)),
            )
            await db.commit()

    async def remove_stock(self, chat_id: int, symbol: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM watchlist_stocks WHERE chat_id = ? AND symbol = ?",
                (chat_id, canonical_symbol(symbol)),
            )
            await db.commit()

    async def add_sector(self, chat_id: int, sector: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO watchlist_sectors(chat_id, sector) VALUES(?, ?)",
                (chat_id, sector.strip()),
            )
            await db.commit()

    async def remove_sector(self, chat_id: int, sector: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM watchlist_sectors WHERE chat_id = ? AND sector = ?",
                (chat_id, sector.strip()),
            )
            await db.commit()

    async def get_watchlist(self, chat_id: int) -> tuple[list[str], list[str]]:
        async with aiosqlite.connect(self.path) as db:
            stock_rows = await db.execute_fetchall(
                "SELECT symbol FROM watchlist_stocks WHERE chat_id = ? ORDER BY symbol",
                (chat_id,),
            )
            sector_rows = await db.execute_fetchall(
                "SELECT sector FROM watchlist_sectors WHERE chat_id = ? ORDER BY sector",
                (chat_id,),
            )
        return ([row[0] for row in stock_rows], [row[0] for row in sector_rows])

    async def get_all_users(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            rows = await db.execute_fetchall("SELECT chat_id FROM users")
        return [row[0] for row in rows]

    async def get_user_symbols(self, chat_id: int) -> set[str]:
        async with aiosqlite.connect(self.path) as db:
            rows = await db.execute_fetchall(
                "SELECT symbol FROM watchlist_stocks WHERE chat_id = ?",
                (chat_id,),
            )
        return {row[0] for row in rows}

    async def insert_event(self, event: Event) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO events(
                    source, symbol, company_name, title, url, pdf_url, published_at,
                    category, raw_text, exchange, cmp, pct_change, revenue, revenue_yoy,
                    ebitda, ebitda_yoy, pat, pat_yoy, materiality_score, tags, summary, key_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.source,
                    event.symbol,
                    event.company_name,
                    event.title,
                    event.url,
                    event.pdf_url,
                    event.published_at.isoformat(),
                    event.category,
                    event.raw_text,
                    event.exchange,
                    event.cmp,
                    event.pct_change,
                    event.revenue,
                    event.revenue_yoy,
                    event.ebitda,
                    event.ebitda_yoy,
                    event.pat,
                    event.pat_yoy,
                    event.materiality_score,
                    json.dumps(event.tags),
                    event.summary,
                    json.dumps(event.key_points),
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def latest_events(self, symbol: str, limit: int = 5):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            return await db.execute_fetchall(
                """
                SELECT * FROM events
                WHERE symbol = ?
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (canonical_symbol(symbol), limit),
            )

    async def latest_for_user(self, chat_id: int, since_iso: str | None = None):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            symbols = await self.get_user_symbols(chat_id)
            if not symbols:
                return []
            placeholders = ",".join("?" for _ in symbols)
            params: list[object] = list(symbols)
            query = f"SELECT * FROM events WHERE symbol IN ({placeholders})"
            if since_iso:
                query += " AND published_at > ?"
                params.append(since_iso)
            query += " ORDER BY published_at DESC LIMIT 50"
            return await db.execute_fetchall(query, tuple(params))

    async def top_announcements_since(self, since_iso: str, limit: int = 20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            return await db.execute_fetchall(
                """
                SELECT * FROM events
                WHERE category = 'announcement' AND published_at >= ?
                ORDER BY materiality_score DESC, published_at DESC
                LIMIT ?
                """,
                (since_iso, limit),
            )

    async def daily_digest(self, day_prefix: str):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            return await db.execute_fetchall(
                """
                SELECT * FROM events
                WHERE category = 'announcement' AND published_at LIKE ?
                ORDER BY materiality_score DESC, published_at DESC
                """,
                (f"{day_prefix}%",),
            )

    async def set_last_notified(self, chat_id: int, timestamp_iso: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET last_notified_at = ? WHERE chat_id = ?",
                (timestamp_iso, chat_id),
            )
            await db.commit()

    async def get_last_notified(self, chat_id: int) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT last_notified_at FROM users WHERE chat_id = ?",
                (chat_id,),
            )
            row = await cursor.fetchone()
        return row[0] if row and row[0] else None

    async def get_telegram_offset(self) -> int | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT value FROM meta WHERE key = 'telegram_offset'"
            )
            row = await cursor.fetchone()
        return int(row[0]) if row and row[0] else None

    async def set_telegram_offset(self, offset: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO meta(key, value) VALUES('telegram_offset', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(offset),),
            )
            await db.commit()
