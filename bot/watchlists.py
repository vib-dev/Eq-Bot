from __future__ import annotations

DEFAULT_WATCHLIST = [
    "BSE", "MCX", "ANGELONE", "MOTILALOFS", "ANANDRATHI", "NUVAMA", "360ONE",
    "PRUDENT", "CAMS", "KFINTECH", "CDSL", "NSDL", "HDFCAMC", "NAM-INDIA",
    "ABSLAMC", "UTIAMC", "JMFINANCIL", "CRISIL", "GROWW", "ICICIAMC",
    "INDIGO", "SPICEJET", "TEXRAIL", "TITAGARH", "RVNL", "RAILTEL", "RITES",
    "JWL", "IRCTC", "GESHIP", "SCI", "ZEEL", "PVRINOX", "SUNTV", "DBCORP",
    "TIPSMUSIC", "NETWORK18", "SAREGAMA", "AMAGI", "PAGEIND", "VTL",
    "KPRMILL", "WELSPUNLIV", "VMART", "ARVIND", "RAYMOND", "ICIL", "GOKEX",
    "LUXIND", "ARVINDFASN", "TRIDENT", "PGIL", "ABFRL", "ABLBL", "NITINSPIN",
    "SAISILK", "GANECOS",
]

DEFAULT_SECTORS = [
    "Capital Market & Wealth",
    "Transport & Railways",
    "Media & Entertainment",
    "Textiles, Apparel & Home",
]

SYMBOL_ALIASES = {
    "360ONE": "360ONE",
    "ICICIAMC": "ICICIPRULI",
}


def canonical_symbol(value: str) -> str:
    symbol = value.strip().upper()
    return SYMBOL_ALIASES.get(symbol, symbol)
