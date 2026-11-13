# Professional Binance Trading Bot

**ربات نوشته‌شده توسط [@shibainuo](https://github.com/shibainuo)**  
**Bot written by [@shibainuo](https://github.com/shibainuo)**

Institutional-style Binance **spot / optional futures** automation with paper trading by default.

> **Disclaimer**  
> Educational software only. Most traders lose money.  
> No profit guarantee. Not financial advice.  
> Always start with `PAPER_MODE=true`.

---

## Author

Created by **@shibainuo**

---

## Highlights

- Paper mode (**$1000 virtual**) + **real Binance prices**
- Fees **0.1%** + slippage **5 bps** in paper fills
- Scored signals (0–100) with ADX / volume filters
- ATR stop, take-profit, **trailing stop**
- Optional **leverage** (capped: low≤2x, medium≤3x, high≤5x)
- Paper **liquidation guard**
- Circuit breakers: daily loss + max drawdown
- 7 live-switchable strategies
- Telegram control panel (colored buttons where supported)
- `/analyze`, `/chart`, `/stats`, CSV trade journal

---

## Quick start

```bash
git clone https://github.com/rezanb111/Professional-Binance-Trading-Bot.git
cd Professional-Binance-Trading-Bot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS
python main.py
```

Telegram → `/start` → **Start Trading**.

---

## Environment

| Variable | Default | Notes |
|----------|---------|--------|
| `PAPER_MODE` | `true` | Virtual balance, real prices |
| `PAPER_BALANCE` | `1000` | Starting virtual USDT |
| `MARKET_TYPE` | `spot` | `spot` or `future` |
| `LEVERAGE` | `1` | Capped by risk profile |
| `RISK_PROFILE` | `medium` | `low` / `medium` / `high` |
| `STRATEGY` | `ema_rsi` | See list below |
| `SYMBOL` | `BTC/USDT` | |
| `TIMEFRAME` | `1h` | |

---

## Telegram commands

| Command | Action |
|---------|--------|
| `/start` | Control panel |
| `/status` | Equity, DD, leverage, position |
| `/stats` | Performance + journal |
| `/analyze` | Technical snapshot |
| `/chart` | Chart image |
| `/strategy` `/strategies` | Switch strategy |
| `/risk` | low / medium / high |
| `/symbol` `/timeframe` | Market |
| `/market spot\|future` | Market type |
| `/leverage 1-5` | Leverage (capped) |
| `/reset_paper` | Reset virtual balance |
| `/close` | Force close |
| `/help` | Help |

---

## Strategies

`ema_rsi` · `macd` · `bollinger` · `supertrend` · `breakout` · `rsi_reversion` · `ichimoku`

---

## Safety

1. Paper for weeks before any real funds  
2. API key: **trade only**, no withdraw, IP whitelist  
3. Leverage multiplies losses — prefer `spot` + `LEVERAGE=1`  
4. Never risk money you cannot afford to lose  

---

**Written by @shibainuo**

MIT License
