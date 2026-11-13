# Professional Binance Trading Bot

Institutional-style **spot** automation for Binance with paper trading by default.

> **Disclaimer**  
> Educational software only. Trading loses money for most people.  
> No guarantees. Not financial advice. Always start in `PAPER_MODE=true`.

---

## Highlights

- **Paper mode ($1000 virtual)** with **real Binance prices**
- Realistic **fees (0.1%)** + **slippage (5 bps)** in paper fills
- **Scored signals** (0–100) – weak setups are filtered
- **Trailing stop** (ATR-based) + hard SL/TP
- **Circuit breakers**: daily loss + max drawdown
- **7 strategies**, switchable live from Telegram
- **Colored Telegram buttons** (Bot API 9.4 styles)
- `/analyze`, `/chart`, `/stats`, trade journal CSV

---

## Quick start

```bash
git clone https://github.com/rezanb111/Professional-Binance-Trading-Bot.git
cd Professional-Binance-Trading-Bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USERS
python main.py
```

Open your bot → `/start` → green **Start Trading**.

Default: `PAPER_MODE=true`, `PAPER_BALANCE=1000`.

---

## Telegram

| Command | Action |
|---------|--------|
| `/start` | Panel |
| `/status` | Equity, DD, signal score, position |
| `/stats` | Win rate, journal |
| `/analyze` | Technical snapshot |
| `/chart` | PNG chart |
| `/strategy name` | Switch strategy |
| `/risk low\|medium\|high` | Risk profile |
| `/symbol` `/timeframe` | Market |
| `/reset_paper` | Reset virtual $1000 |
| `/close` | Force close |

---

## Strategies

`ema_rsi` · `macd` · `bollinger` · `supertrend` · `breakout` · `rsi_reversion` · `ichimoku`

---

## Safety

1. Paper first for weeks  
2. API key: trade only, no withdraw, IP whitelist  
3. Never trust any bot with money you cannot lose  

MIT License
