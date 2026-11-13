# Professional Binance Trading Bot

**Multi-strategy automated spot trading system for Binance**  
Full Telegram remote control · Technical analysis · Live charts · Risk profiles · Production architecture

> **⚠️ CRITICAL DISCLAIMER**  
> Educational / research use only.  
> You can lose money. No guarantees. Not financial advice.  
> Always start on **Testnet** + `DRY_RUN=true`.

---

## What You Get

### Strategies (switchable live via Telegram)
| Name | Style |
|------|--------|
| `ema_rsi` | EMA crossover + RSI + volume |
| `macd` | MACD line/signal crossover |
| `bollinger` | Bollinger mean reversion |
| `supertrend` | ATR Supertrend style |
| `breakout` | Donchian channel breakout |
| `rsi_reversion` | Classic RSI oversold/overbought |
| `ichimoku` | Ichimoku cloud + TK cross |

### Telegram Control
- Start / Stop engine
- Change risk profile (`low` / `medium` / `high`)
- Switch strategy on the fly
- `/analyze` → full technical summary (Trend, RSI, ADX, Bollinger, MACD, EMAs...)
- `/chart` → real PNG chart with price, EMAs, Bollinger, RSI, MACD
- Force close position
- Live status, equity, notifications on every trade

### Risk Engine
- Fixed-fractional position sizing
- ATR-based stops & take-profits
- Daily loss + max drawdown circuit breakers

---

## Quick Start

```bash
git clone https://github.com/rezanb111/Professional-Binance-Trading-Bot.git
cd Professional-Binance-Trading-Bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your keys + Telegram token + your user ID
python main.py
```

Then open your bot in Telegram → `/start`

---

## Main Telegram Commands

```
/start          Control panel + keyboard
/status         Live status
/analyze        Technical analysis
/chart          Send chart image
/strategy name  Switch strategy
/strategies     List all strategies
/risk low|medium|high
/start_bot      Enable trading
/stop_bot       Disable trading
/close          Force close position
```

---

## Security

- Only your Telegram user ID can control the bot
- Binance key: Trade only, no Withdraw + IP whitelist
- Start with Testnet + Dry-Run

---

## License

MIT
