# Market Monitor Telegram Bot

This project is a free-first Telegram bot for Indian market analysts. It is designed to:

- poll official/free sources every 5 minutes
- suppress stale items by only forwarding freshly published events within the configured freshness window
- track user watchlists inside Telegram
- summarize news and corporate announcements
- generate daily and on-demand reports
- answer simple interactive questions from stored news and announcement history
- send an automatic 7 AM IST market-wide briefing since last market close

## Important constraints

- BSE announcements are handled through official/public pages.
- Reuters is disabled in the GitHub Actions deployment because Reuters blocks these unauthenticated requests from hosted runners.
- ScanX support parses the public company-filings table and only keeps rows where a reported time can be extracted.
- "Completely free forever" hosting cannot be guaranteed by code alone. The project is structured so it can run locally, on a free hobby VPS, or on a free-tier worker when available.
- AI summarization defaults to an embedded heuristic summarizer so the bot still works without paid inference. You can later swap in an external model if you want richer summaries.

## Features

- Multi-user watchlists with independent stock/sector preferences
- Real-time style polling loop every 5 minutes
- Per-update message format with:
  - company name and symbol
  - CMP and last-close delta when quote lookup succeeds
  - AI-style gist
  - 3-5 key pointers
  - source/PDF link
  - revenue, EBITDA, PAT YoY metrics when extracted
- Daily material announcements report
- "Since last close" report for top announcements
- `/wake` command to confirm whether anything new has arrived since the last response
- `/ask` command for interactive querying over stored data
- hourly heartbeat message so you know the bot is still running even if there are no new alerts
- automatic 7 AM IST market brief for all users

## GitHub Actions deployment

This is the recommended free-hosted mode.

1. Create a GitHub repository for this project.
2. Add a repository secret named `TELEGRAM_BOT_TOKEN`.
3. Push this code.
4. Enable GitHub Actions for the repository.
5. Start a run manually from the Actions tab once, then send `/start` to the bot in Telegram.

How it works:

- GitHub Actions runs every 5 minutes.
- Each run pulls new source items, handles any Telegram commands received since the last run, sends alerts, and writes updated state to `data/bot.db`.
- The workflow commits `data/` back to the repository so the bot remembers users, watchlists, and already-seen updates.
- An hourly heartbeat can confirm the bot is still healthy even when there are no new matched items.
- The bot drops items older than the configured freshness window so the feed stays focused on newly published updates.
- Around 7:00 AM IST it automatically sends a market-wide briefing covering macro and company updates since the last market close.

Important notes:

- If the repository is public, committed database state is public too.
- If the repository is private, GitHub Free includes limited Actions minutes. Whether it fits depends on how fast each run finishes.
- Rotate the Telegram bot token before deployment because the old token was exposed in chat.

## Local quick start

1. Install Python 3.11+.
2. Create a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN`.
5. Run `python -m bot`.

## Telegram commands

- `/start` register and seed the default watchlist
- `/watchlist` show your current stocks
- `/help` show commands
- `/status` show health, last workflow run, and stored event count
- `/addstock SYMBOL`
- `/add SYMBOL`
- `/removestock SYMBOL`
- `/remove SYMBOL`
- `/addsector sector-name`
- `/removesector sector-name`
- `/latest SYMBOL` latest 5 stored updates for a company
- `/report` top material watchlist updates since the last market close
- `/dailyreport` market-wide most important updates since the last market close
- `/morningreport` same as `/dailyreport`
- `/wake` confirm whether anything new has arrived since the bot last messaged you
- `/ask QUESTION` ask about stored company events and recent summaries

## Files

- `bot/config.py` runtime configuration
- `bot/db.py` SQLite schema and queries
- `bot/main.py` app entry point
- `bot/services/` reporting, summarization, filtering, metrics extraction
- `bot/sources/` source pollers
- `bot/watchlists.py` seeded stock universe and aliases
