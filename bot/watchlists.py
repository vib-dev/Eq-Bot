from __future__ import annotations

import re

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

MARKET_SYMBOL = "MARKET"

RESEARCH_UNIVERSE = {
    "BSE": {"name": "BSE Limited", "aliases": ["BSE LIMITED", "BSE"]},
    "MCX": {"name": "Multi Commodity Exchange of India", "aliases": ["MULTI COMMODITY EXCHANGE", "MCX"]},
    "ANGELONE": {"name": "Angel One", "aliases": ["ANGEL ONE", "ANGELONE"]},
    "MOTILALOFS": {"name": "Motilal Oswal Financial Services", "aliases": ["MOTILAL OSWAL", "MOTILAL OSWAL FINANCIAL SERVICES", "MOTILALOFS"]},
    "ANANDRATHI": {"name": "Anand Rathi Wealth", "aliases": ["ANAND RATHI", "ANAND RATHI WEALTH", "ANANDRATHI"]},
    "NUVAMA": {"name": "Nuvama Wealth Management", "aliases": ["NUVAMA", "NUVAMA WEALTH"]},
    "360ONE": {"name": "360 ONE WAM", "aliases": ["360 ONE", "360 ONE WAM", "IIFL WEALTH", "360ONE"]},
    "PRUDENT": {"name": "Prudent Corporate Advisory Services", "aliases": ["PRUDENT", "PRUDENT CORPORATE"]},
    "CAMS": {"name": "Computer Age Management Services", "aliases": ["COMPUTER AGE MANAGEMENT", "CAMS"]},
    "KFINTECH": {"name": "KFin Technologies", "aliases": ["KFIN TECHNOLOGIES", "KFINTECH"]},
    "CDSL": {"name": "Central Depository Services", "aliases": ["CENTRAL DEPOSITORY SERVICES", "CDSL"]},
    "NSDL": {"name": "National Securities Depository", "aliases": ["NATIONAL SECURITIES DEPOSITORY", "NSDL"]},
    "HDFCAMC": {"name": "HDFC Asset Management Company", "aliases": ["HDFC AMC", "HDFC ASSET MANAGEMENT"]},
    "NAM-INDIA": {"name": "Nippon Life India Asset Management", "aliases": ["NIPPON LIFE INDIA ASSET MANAGEMENT", "NIPPON LIFE INDIA AMC", "NAM INDIA", "NAM-INDIA"]},
    "ABSLAMC": {"name": "Aditya Birla Sun Life AMC", "aliases": ["ADITYA BIRLA SUN LIFE AMC", "ABSL AMC", "ABSLAMC"]},
    "UTIAMC": {"name": "UTI Asset Management Company", "aliases": ["UTI AMC", "UTI ASSET MANAGEMENT", "UTIAMC"]},
    "JMFINANCIL": {"name": "JM Financial", "aliases": ["JM FINANCIAL", "JMFINANCIL"]},
    "CRISIL": {"name": "CRISIL", "aliases": ["CRISIL"]},
    "GROWW": {"name": "Groww", "aliases": ["GROWW"]},
    "ICICIAMC": {"name": "ICICI AMC", "aliases": ["ICICI AMC", "ICICI ASSET MANAGEMENT", "ICICIAMC"]},
    "INDIGO": {"name": "InterGlobe Aviation", "aliases": ["INTERGLOBE AVIATION", "INDIGO"]},
    "SPICEJET": {"name": "SpiceJet", "aliases": ["SPICEJET"]},
    "TEXRAIL": {"name": "Texmaco Rail & Engineering", "aliases": ["TEXMACO RAIL", "TEXRAIL"]},
    "TITAGARH": {"name": "Titagarh Rail Systems", "aliases": ["TITAGARH RAIL", "TITAGARH RAIL SYSTEMS", "TITAGARH"]},
    "RVNL": {"name": "Rail Vikas Nigam", "aliases": ["RAIL VIKAS NIGAM", "RVNL"]},
    "RAILTEL": {"name": "RailTel Corporation of India", "aliases": ["RAILTEL", "RAILTEL CORPORATION"]},
    "RITES": {"name": "RITES", "aliases": ["RITES"]},
    "JWL": {"name": "Jupiter Wagons", "aliases": ["JUPITER WAGONS", "JWL"]},
    "IRCTC": {"name": "IRCTC", "aliases": ["IRCTC"]},
    "GESHIP": {"name": "The Great Eastern Shipping Company", "aliases": ["GREAT EASTERN SHIPPING", "GESHIP"]},
    "SCI": {"name": "Shipping Corporation of India", "aliases": ["SHIPPING CORPORATION OF INDIA", "SCI"]},
    "ZEEL": {"name": "Zee Entertainment Enterprises", "aliases": ["ZEE ENTERTAINMENT", "ZEEL"]},
    "PVRINOX": {"name": "PVR INOX", "aliases": ["PVR INOX", "PVRINOX"]},
    "SUNTV": {"name": "Sun TV Network", "aliases": ["SUN TV", "SUN TV NETWORK", "SUNTV"]},
    "DBCORP": {"name": "DB Corp", "aliases": ["DB CORP", "DBCORP"]},
    "TIPSMUSIC": {"name": "Tips Industries", "aliases": ["TIPS INDUSTRIES", "TIPS MUSIC", "TIPSMUSIC"]},
    "NETWORK18": {"name": "Network18 Media & Investments", "aliases": ["NETWORK18", "NETWORK 18"]},
    "SAREGAMA": {"name": "Saregama India", "aliases": ["SAREGAMA", "SAREGAMA INDIA"]},
    "AMAGI": {"name": "Amagi", "aliases": ["AMAGI"]},
    "PAGEIND": {"name": "Page Industries", "aliases": ["PAGE INDUSTRIES", "PAGEIND"]},
    "VTL": {"name": "Vardhman Textiles", "aliases": ["VARDHMAN TEXTILES", "VTL"]},
    "KPRMILL": {"name": "KPR Mill", "aliases": ["KPR MILL", "KPRMILL"]},
    "WELSPUNLIV": {"name": "Welspun Living", "aliases": ["WELSPUN LIVING", "WELSPUNLIV"]},
    "VMART": {"name": "V-Mart Retail", "aliases": ["V MART", "V-MART", "VMART"]},
    "ARVIND": {"name": "Arvind", "aliases": ["ARVIND"]},
    "RAYMOND": {"name": "Raymond", "aliases": ["RAYMOND"]},
    "ICIL": {"name": "ICIL", "aliases": ["ICIL"]},
    "GOKEX": {"name": "Gokaldas Exports", "aliases": ["GOKALDAS EXPORTS", "GOKEX"]},
    "LUXIND": {"name": "Lux Industries", "aliases": ["LUX INDUSTRIES", "LUXIND"]},
    "ARVINDFASN": {"name": "Arvind Fashions", "aliases": ["ARVIND FASHIONS", "ARVINDFASN"]},
    "TRIDENT": {"name": "Trident", "aliases": ["TRIDENT"]},
    "PGIL": {"name": "Pearl Global Industries", "aliases": ["PEARL GLOBAL INDUSTRIES", "PGIL"]},
    "ABFRL": {"name": "Aditya Birla Fashion and Retail", "aliases": ["ADITYA BIRLA FASHION", "ABFRL"]},
    "ABLBL": {"name": "ABLBL", "aliases": ["ABLBL"]},
    "NITINSPIN": {"name": "Nitin Spinners", "aliases": ["NITIN SPINNERS", "NITINSPIN"]},
    "SAISILK": {"name": "Sai Silks", "aliases": ["SAI SILKS", "SAISILK"]},
    "GANECOS": {"name": "Ganesh Ecosphere", "aliases": ["GANESH ECOSPHERE", "GANECOS"]},
}


def canonical_symbol(value: str) -> str:
    symbol = value.strip().upper()
    return symbol


def company_name_for_symbol(symbol: str) -> str:
    return RESEARCH_UNIVERSE.get(symbol, {}).get("name", symbol)


def match_tracked_symbol(text: str) -> str | None:
    normalized = _normalized_text(text)
    best_symbol: str | None = None
    best_length = 0
    for symbol, meta in RESEARCH_UNIVERSE.items():
        for alias in meta["aliases"]:
            alias_norm = _normalized_text(alias)
            if _contains_alias(normalized, alias_norm) and len(alias_norm) > best_length:
                best_symbol = symbol
                best_length = len(alias_norm)
    return best_symbol


def normalize_company_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", name.upper())
    return cleaned[:12] or "UNKNOWN"


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9&]+", " ", text.upper())).strip()


def _contains_alias(text: str, alias: str) -> bool:
    if len(alias) <= 4:
        return re.search(rf"\b{re.escape(alias)}\b", text) is not None
    return alias in text
