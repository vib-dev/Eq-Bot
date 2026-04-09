from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    bot_timezone: str = "Asia/Kolkata"
    db_path: str = "data/bot.db"
    poll_interval_minutes: int = 5
    enable_reuters: bool = True
    enable_moneycontrol: bool = True
    enable_bse: bool = True
    enable_scanx: bool = False
    enable_heartbeat: bool = True
    default_market_cap_threshold_crore: int = 1000
    max_updates_per_cycle: int = 20
    http_timeout_seconds: int = 20
    real_time_freshness_minutes: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            bot_timezone=os.getenv("BOT_TIMEZONE", "Asia/Kolkata"),
            db_path=os.getenv("DB_PATH", "data/bot.db"),
            poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "5")),
            enable_reuters=_bool_env("ENABLE_REUTERS", True),
            enable_moneycontrol=_bool_env("ENABLE_MONEYCONTROL", True),
            enable_bse=_bool_env("ENABLE_BSE", True),
            enable_scanx=_bool_env("ENABLE_SCANX", True),
            enable_heartbeat=_bool_env("ENABLE_HEARTBEAT", True),
            default_market_cap_threshold_crore=int(os.getenv("DEFAULT_MARKET_CAP_THRESHOLD_CRORE", "1000")),
            max_updates_per_cycle=int(os.getenv("MAX_UPDATES_PER_CYCLE", "20")),
            http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            real_time_freshness_minutes=int(os.getenv("REAL_TIME_FRESHNESS_MINUTES", "15")),
        )

    def ensure_paths(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
