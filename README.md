# Professional Binance Trading Bot

**Institutional-grade automated spot trading system for Binance**  
Multi-risk profiles · Advanced position sizing · Technical strategy engine · Production-ready architecture

> **⚠️ CRITICAL DISCLAIMER**  
> This software is provided **strictly for educational and research purposes**.  
> Cryptocurrency trading involves substantial risk of loss and is not suitable for every investor.  
> Past performance is not indicative of future results.  
> **You can lose some or all of your capital.**  
> The authors and contributors accept **no liability** for any financial losses incurred through the use of this software.  
> Always start on **Binance Testnet** / paper trading mode. Never risk money you cannot afford to lose.  
> This is **not financial advice**.

---

## Features

- **Three distinct risk profiles**
  - `low` — Conservative (0.5% risk per trade, wider stops, stricter filters)
  - `medium` — Balanced (1.0% risk per trade)
  - `high` — Aggressive (2.0% risk per trade, tighter stops, more frequent signals)

- **Professional risk management**
  - Fixed-fractional position sizing based on account equity and stop distance
  - ATR-based dynamic stop-loss & take-profit
  - Maximum concurrent positions limit
  - Daily loss circuit breaker
  - Exchange-native stop-loss orders (recommended)

- **Strategy engine**
  - EMA crossover (fast / slow) + RSI filter + volume confirmation
  - Fully configurable parameters per risk profile
  - Clean separation of signal generation and execution

- **Production architecture**
  - CCXT (unified exchange interface)
  - Async-ready design
  - Structured logging (JSON + console)
  - Environment-based configuration (`.env`)
  - Dry-run / paper trading mode by default
  - Graceful shutdown & error handling
  - Docker support

- **Security best practices**
  - No hardcoded secrets
  - Trade-only API key permissions recommended
  - IP whitelist strongly advised
  - Never enable withdrawal permissions

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rezanb111/Professional-Binance-Trading-Bot.git
cd Professional-Binance-Trading-Bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_testnet_or_live_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true          # ALWAYS start with true
RISK_PROFILE=medium           # low | medium | high
SYMBOL=BTC/USDT
TIMEFRAME=1h
DRY_RUN=true                  # true = paper trading (no real orders)
```

### 3. Run

```bash
python main.py
```

---

## Risk Profiles

| Profile  | Risk per Trade | ATR Multiplier (Stop) | Max Positions | Entry Strictness |
|----------|----------------|-----------------------|---------------|------------------|
| `low`    | 0.5%           | 3.0×                  | 1             | High             |
| `medium` | 1.0%           | 2.0×                  | 2             | Medium           |
| `high`   | 2.0%           | 1.5×                  | 3             | Lower            |

Position size is calculated so that if the stop is hit, the account loses approximately the configured risk percentage.

---

## Architecture Overview

```
src/
├── exchange/
│   └── client.py          # CCXT Binance wrapper (testnet + live)
├── strategy/
│   ├── base.py            # Abstract strategy interface
│   └── ema_rsi.py         # EMA + RSI + Volume strategy
├── risk/
│   └── manager.py         # Position sizing, circuit breakers, limits
├── indicators/
│   └── technical.py       # EMA, RSI, ATR, etc.
├── core/
│   └── bot.py             # Main trading loop & orchestration
└── utils/
    ├── logger.py
    └── helpers.py
```

---

## Recommended Workflow

1. **Paper / Testnet only** for at least several weeks
2. Backtest the strategy thoroughly (you can extend the engine)
3. Start live with the smallest capital you are comfortable losing
4. Monitor logs and equity curve daily
5. Never leave a live bot unattended without exchange-side stop-loss orders
6. Use a VPS with good uptime and synchronized system clock

---

## Security Checklist

- [ ] API key has **only** Spot Trading permission
- [ ] Withdrawal permission is **disabled**
- [ ] IP whitelist is configured on Binance
- [ ] Secrets live only in `.env` (never committed)
- [ ] `DRY_RUN=true` until you are 100% confident
- [ ] You understand every line of the risk management code

---

## Disclaimer (Read Again)

This project is an **educational framework**.  
It does **not** guarantee profits. Markets are adversarial and non-stationary.  
Any trading decision and its consequences remain solely your responsibility.

---

## License

MIT License – see [LICENSE](LICENSE)

---

**Built for serious learners who respect risk.**
