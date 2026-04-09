from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Event:
    source: str
    symbol: str
    company_name: str
    title: str
    url: str
    published_at: datetime
    category: str
    raw_text: str = ""
    pdf_url: str | None = None
    exchange: str | None = None
    cmp: float | None = None
    pct_change: float | None = None
    revenue: str | None = None
    revenue_yoy: str | None = None
    ebitda: str | None = None
    ebitda_yoy: str | None = None
    pat: str | None = None
    pat_yoy: str | None = None
    materiality_score: int = 0
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    key_points: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserProfile:
    chat_id: int
    username: str | None
    first_name: str | None

