import os
import asyncio
import logging
import json
import time
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import yfinance as yf
from google import genai
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECRETS & CLIENT ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_KEY)
except Exception as e:
    logger.error(f"Failed to initialize AI: {e}")

# --- ENHANCED USER DATABASE (Watchlists + Settings) ---
USER_DATA_FILE = "/tmp/system_db.json"

INITIAL_WATCHLIST =[
    "BSE", "MCX", "ANGELONE", "MOTILALOFS", "ANANDRATHI", "NUVAMA", "360ONE", "PRUDENT", "CAMS", "KFINTECH", "CDSL", "HDFCAMC", "NAM-INDIA", "ABSLAMC", "UTIAMC", "JMFINANCIL", "CRISIL", "GROWW", "ICICIAMC",
    "INDIGO", "SPICEJET", "TEXRAIL", "TITAGARH", "RVNL", "RAILTEL", "RITES", "JWL", "IRCTC", "GESHIP", "SCI",
    "ZEEL", "PVRINOX", "SUNTV", "DBCORP", "TIPSMUSIC", "NETWORK18", "SAREGAMA", "AMAGI",
    "PAGEIND", "VTL", "KPRMILL", "WELSPUNLIV", "VMART", "ARVIND", "RAYMOND", "ICIL", "GOKEX", "LUXIND", "ARVINDFASN", "TRIDENT", "PGIL", "ABFRL", "ABLBL", "NITINSPIN", "SAISILK", "GANECOS"
]

processed_news_ids = set()
stock_cache = {} # Cache long names to speed up loops

def load_db():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"watchlists": {}, "tv_pref": {}}

def save_db(data):
    with open(USER_DATA_FILE, 'w') as f: json.dump(data, f)

# --- HYBRID INTELLIGENCE ENGINE ---

async def get_stock_metrics(symbol):
    if symbol not in stock_cache:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            stock_cache[symbol] = ticker.info.get('shortName', symbol)
        except: stock_cache[symbol] = symbol

    name = stock_cache[symbol]
    
    try:
        t = yf.Ticker(f"{symbol}.NS").fast_info
        cmp = t.get('last_price', 0)
        pc = t.get('previous_close', 1)
        chg = ((cmp - pc) / pc) * 100 if pc else 0
        mc = t.get('market_cap', 0) / 1e7
        return round(cmp, 2), round(chg, 2), mc, name
    except: return 0, 0, 0, name

async def fetch_dual_net_news(symbol, company_name):
    """
    Scrapes both Yahoo Finance Backend + LiveMint / Google News dynamically.
    Combines to form the absolute net for 0 missed notifications.
    """
    updates =[]
    
    # NET 1: YFinance Immediate Push
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        for news in ticker.news[:2]:
            updates.append({"title": news.get('title'), "link": news.get('link'), "id": news.get('uuid', str(time.time())), "text": "Corporate details in linked article."})
    except: pass

    # NET 2: LiveMint / Strict RSS Push (Overriding Caches)
    ts = int(time.time())
    query = urllib.parse.quote(f'"{company_name}" OR "{symbol}" (announcement OR results OR updates) (LiveMint OR BSE)')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en&scoring=n&cb={ts}"
    feed = feedparser.parse(url)
    
    for e in feed.entries[:2]:
        body = BeautifulSoup(e.description, "html.parser").get_text(" ") if hasattr(e, 'description') else ""
        updates.append({"title": e.title, "link": e.link, "id": e.id, "text": body})
        
    return updates

async def ai_finxray_analyzer(context_title, context_body, symbol, name, tv_enabled):
    """
    Tier-1 Engine: Filters hallucinations, implements "GQ/Quest" styles.
    Checks explicitly against BSE/CDSL identity false positives.
    """
    tv_prompt = """
    TV1:[Create punchy TV ticker sentence 1, 5-8 words max. UPPERCASE.]
    TV2:[Create punchy TV ticker sentence 2, 5-8 words max. UPPERCASE.]
    """ if tv_enabled else ""

    prompt = f"""
    You are an Elite Institutional Equity Analyst parsing breaking news for {name} ({symbol}).
    TITLE: {context_title}
    BODY: {context_body[:900]}

    **MANDATORY CHECK ONE (THE "VIRAT" PROTOCOL):** 
    If {name} ({symbol}) is JUST mentioned as the stock exchange platform (e.g. another company wrote a letter "TO the BSE"), return ONLY the word: REJECT.
    We only want news WHERE {name} is the central business making the announcement or releasing earnings.

    If valid, generate EXACTLY this format (NO extra conversational text):
    SUBJECT: [Extract accurate 1-line business essence]
    {tv_prompt}[IF NEWS CONTAINS EARNINGS/RESULTS, use tag 📊 QUARTER HIGHLIGHTS:]
    📊 QUARTER HIGHLIGHTS:
    • [Revenue metrics + YoY %]
    •[EBITDA/Net Profit Margin + YoY/QoQ %]
    • [Dividend or crucial volume guidance][IF GENERAL CORPORATE NEWS, use tag 🔍 STRATEGIC INSIGHTS:]
    🔍 STRATEGIC INSIGHTS:
    • [Material update detail 1]
    • [Impact analysis factor 2]
    """
    
    try:
        res = await asyncio.to_thread(ai_client.models.generate_content, model='gemini-2.5-flash', contents=prompt)
        text = res.text.strip()
        
        # Stop False Positives Dead in their Tracks
        if "REJECT" in text.upper()[:15]:
            return None 

        return text
    except Exception as e:
        logger.error(f"AI Parse Error: {e}")
        return None

async def package_notification(item, symbol, cmp, chg, name, tv_enabled):
    analysis_block = await ai_finxray_analyzer(item['title'], item['text'], symbol, name, tv_enabled)
    
    # Trigger False Positive protection - Abort send
    if not analysis_block: return None 

    color = "🟢" if chg > 0 else "🔴" if chg < 0 else "🟡"
    sym_chg = f"+{chg}" if chg > 0 else f"{chg}"
    
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    ist = now.strftime("%d %b %Y · %H:%M IST")

    query = urllib.parse.quote(f"Evaluate this Indian Corporate announcement: {item['link']}")
    gemini_link = f"https://gemini.google.com/app?q={query}"

    final_msg = (
        f"{color} **{name}** | {symbol}\n"
        f"₹{cmp} ({sym_chg}%) · 🕒 {ist}\n\n"
        f"{analysis_block}\n\n"
        f"🔗 [Official Filing/Article]({item['link']})\n"
        f"⚡ [Analyze with Gemini AI App]({gemini_link})"
    )
    return final_msg

# --- TELEGRAM BOT ROUTING ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_chat.id)
    db = load_db()
    if uid not in db['watchlists']: db['watchlists'][uid] = INITIAL_WATCHLIST
    save_db(db)
    await update.message.reply_text(
        "💼 **GQ/FinXRay Caliber AI Initialized.**\n\n"
        "🟢 Auto-Detects Earnings: Prints \"Quarter Highlights\" margins directly.\n"
        "🛑 Smart Reject Active: Automatically ignores irrelevant Exchange clarifications.\n"
        "⚙️ Use `/graphics ON` to enable TV Chyron texts for breaking feeds.\n"
        "Try fetching specific metrics with: `/latest RVNL`"
    )

async def toggle_graphics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_chat.id)
    state = "ON" if context.args and context.args[0].upper() == "ON" else "OFF"
    db = load_db()
    
    if 'tv_pref' not in db: db['tv_pref'] = {}
    db['tv_pref'][uid] = (state == "ON")
    save_db(db)
    
    await update.message.reply_text(f"📺 TV Graphics formatting is now set to: **{state}**.")

async def pull_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Cmd requires valid ticker: `/latest CDSL`", parse_mode="Markdown")
    sym = context.args[0].upper()
    uid = str(update.effective_chat.id)
    db = load_db()
    tv_on = db.get('tv_pref', {}).get(uid, False)
    
    loading = await update.message.reply_text(f"📡 Querying Multi-net Intelligence for {sym}...")
    cmp, chg, mc, name = await get_stock_metrics(sym)
    items = await fetch_dual_net_news(sym, name)

    if not items:
        return await loading.edit_text(f"Zero highly relevant results or filings processed in past 24Hrs for {name}.")

    await loading.delete()
    sent_something = False
    
    for i in items:
        # Pre-process duplication on exact requests
        if i['id'] not in processed_news_ids:
            payload = await package_notification(i, sym, cmp, chg, name, tv_on)
            if payload:
                processed_news_ids.add(i['id'])
                sent_something = True
                await update.message.reply_text(payload, parse_mode="Markdown", disable_web_page_preview=True)

    if not sent_something:
        await update.message.reply_text("AI correctly swept the wire but determined hits were 'Irrelevant / Noise / Other Entity Mentions' and auto-discarded them to save your time.")

async def hyper_watchdog(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    targets = set(t for tracks in db.get('watchlists', {}).values() for t in tracks)

    for ticker in targets:
        await asyncio.sleep(0.5) 
        cmp, chg, mc, name = await get_stock_metrics(ticker)
        
        # Protect noise floor for irrelevant low caps
        if mc < 1000 and mc != 0: continue

        batch = await fetch_dual_net_news(ticker, name)
        
        for news in batch:
            if news['id'] not in processed_news_ids:
                processed_news_ids.add(news['id'])
                if len(processed_news_ids) > 1000: processed_news_ids.clear()
                
                # We analyze it for global validity just ONCE.
                test_tv_param = False # Base check assumes false to save AI tokens globally, formatting alters locally
                payload = None # Generate payload conditionally depending on target preferences
                valid_checked = False
                is_valid = False

                for uid, subs in db.get('watchlists', {}).items():
                    if ticker in subs:
                        if not valid_checked:
                            # Before processing the visual output, let AI perform strict verify
                            valid_block = await ai_finxray_analyzer(news['title'], news['text'], ticker, name, False)
                            valid_checked = True
                            if not valid_block: break # AI Said REJECT. Cease immediately globally.
                            is_valid = True

                        if is_valid:
                            # Apply their visual preference for transmission
                            wants_tv = db.get('tv_pref', {}).get(uid, False)
                            custom_push = await package_notification(news, ticker, cmp, chg, name, wants_tv)
                            try:
                                if custom_push:
                                    await context.bot.send_message(chat_id=uid, text=custom_push, parse_mode="Markdown", disable_web_page_preview=True)
                            except: pass
        await asyncio.sleep(0.5)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", pull_latest))
    app.add_handler(CommandHandler("graphics", toggle_graphics))

    q = app.job_queue
    if q: q.run_repeating(hyper_watchdog, interval=180, first=5)
    
    logger.info("🟢 Quest-Class Architecture Initialized.")
    app.run_polling()

if __name__ == "__main__":
    main()
