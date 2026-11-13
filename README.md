# Professional Binance Trading Bot

**Institutional-grade automated spot trading system for Binance**  
Full Telegram remote control · Multi-risk profiles · Advanced risk management · Production-ready

> **⚠️ CRITICAL DISCLAIMER**  
> This software is provided **strictly for educational and research purposes**.  
> Cryptocurrency trading involves substantial risk of loss.  
> **You can lose some or all of your capital.**  
> The authors accept **no liability** for any financial losses.  
> Always start on **Binance Testnet** + `DRY_RUN=true`.  
> This is **not financial advice**.

---

## Key Features

### Telegram Full Control Panel
- Start / Stop trading engine remotely
- Change risk profile (`low` / `medium` / `high`) on the fly
- Live status, equity, open position, last signal
- Force close position
- Instant trade notifications (entry / exit / errors / circuit breaker)
- Inline keyboard for one-tap control
- Only authorized Telegram user IDs can control the bot

### Trading Engine
- Three distinct risk profiles with different position sizing, stops and filters
- Fixed-fractional risk management (risk % of equity per trade)
- ATR-based dynamic stop-loss & take-profit
- Daily loss + max drawdown circuit breakers
- EMA Crossover + RSI + Volume strategy (extensible)
- Dry-run mode by default
- Clean modular architecture

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rezanb111/Professional-Binance-Trading-Bot.git
cd Professional-Binance-Trading-Bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the token
3. Get your user ID from [@userinfobot](https://t.me/userinfobot)

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BINANCE_TESTNET=true
DRY_RUN=true
RISK_PROFILE=medium
SYMBOL=BTC/USDT
TIMEFRAME=1h

TELEGRAM_BOT_TOKEN=123456:ABC-...
TELEGRAM_ALLOWED_USERS=123456789          # your Telegram ID
```

### 4. Run

```bash
python main.py
```

Then open your bot in Telegram and send `/start`.

---

## Telegram Commands & Buttons

| Command / Button      | Action                              |
|-----------------------|-------------------------------------|
| `/start`              | Open control panel + keyboard       |
| `/status`             | Full live status                    |
| `/balance`            | Current equity                      |
| `/start_bot`          | Enable trading loop                 |
| `/stop_bot`           | Disable trading loop                |
| `/risk low\|medium\|high` | Change risk profile on the fly  |
| `/close`              | Force close open position           |
| Inline buttons        | Same actions with one tap           |

You also receive automatic notifications for:
- New entries / exits
- Risk profile changes
- Circuit breaker triggers
- Engine errors

---

## Risk Profiles

| Profile  | Risk/Trade | ATR Stop | Max Positions | Style          |
|----------|------------|----------|---------------|----------------|
| `low`    | 0.5%       | 3.0×     | 1             | Conservative   |
| `medium` | 1.0%       | 2.0×     | 2             | Balanced       |
| `high`   | 2.0%       | 1.5×     | 3             | Aggressive     |

---

## Security Checklist

- [ ] Telegram: only your user ID in `TELEGRAM_ALLOWED_USERS`
- [ ] Binance API key: **Trade only**, no Withdraw
- [ ] IP whitelist enabled on Binance
- [ ] `DRY_RUN=true` until thoroughly tested
- [ ] Start on Testnet
- [ ] Never share your `.env` or bot token

---

## Architecture

```
src/
├── core/
│   ├── bot.py          # Trading engine (controlled by state)
│   └── state.py        # Thread-safe shared state
├── exchange/
│   └── client.py       # CCXT Binance wrapper
├── strategy/
│   ├── base.py
│   └── ema_rsi.py
├── risk/
│   └── manager.py
├── telegram/
│   ├── app.py          # Application + notification worker
│   └── handlers.py     # Commands & inline buttons
├── indicators/
│   └── technical.py
└── utils/
    ├── logger.py
    └── helpers.py
```

---

## Recommended Workflow

1. Run on Testnet + Dry-Run for days/weeks
2. Monitor via Telegram
3. Switch to live only with very small capital
4. Keep exchange-side stop-loss orders when possible
5. Use a VPS for 24/7 operation

---

## License

MIT License

---

**Built for serious users who respect risk management.**
