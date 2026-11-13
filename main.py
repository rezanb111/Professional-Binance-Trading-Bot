#!/usr/bin/env python3
"""
Professional Binance Trading Bot
Written by @shibainuo
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.bot import TradingBot
from src.core.state import BotState
from src.exchange.client import BinanceClient
from src.telegram.app import build_telegram_app, notification_worker
from src.utils.logger import setup_logger

import src.strategy  # noqa: F401

AUTHOR = "@shibainuo"


def load_config() -> dict:
    with open(ROOT / "config" / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_trading_loop(bot: TradingBot) -> None:
    bot.run()


async def main_async() -> None:
    load_dotenv()
    setup_logger(os.getenv("LOG_LEVEL", "INFO"))

    paper_mode = os.getenv("PAPER_MODE", "true").lower() in ("1", "true", "yes")
    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        paper_mode = True

    testnet = os.getenv("BINANCE_TESTNET", "false").lower() in ("1", "true", "yes")
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")

    market_type = os.getenv("MARKET_TYPE", "spot").lower()
    if market_type not in ("spot", "future"):
        market_type = "spot"

    try:
        leverage = max(1, int(os.getenv("LEVERAGE", "1")))
    except ValueError:
        leverage = 1

    risk_profile = os.getenv("RISK_PROFILE", "medium").lower()
    strategy_name = os.getenv("STRATEGY", "ema_rsi").lower()
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1h")
    paper_balance = float(os.getenv("PAPER_BALANCE", "1000"))

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")

    if not telegram_token or not allowed_users.strip():
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS required")
        sys.exit(1)

    if not paper_mode and (not api_key or not api_secret):
        logger.error("Live mode needs API keys")
        sys.exit(1)

    if risk_profile not in ("low", "medium", "high"):
        logger.error("RISK_PROFILE must be low|medium|high")
        sys.exit(1)

    cfg = load_config()
    caps = cfg.get("leverage", {}).get("max_by_profile", {})
    cap = int(caps.get(risk_profile, 3))
    if market_type == "future":
        leverage = min(leverage, cap)
    else:
        leverage = 1

    state = BotState(
        risk_profile=risk_profile,
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        paper_mode=paper_mode,
        testnet=testnet and not paper_mode,
        market_type=market_type,
        leverage=leverage,
        paper_cash=paper_balance,
        paper_start_balance=paper_balance,
        equity=paper_balance,
        trading_enabled=False,
    )

    logger.info("=" * 60)
    logger.info("Professional Binance Trading Bot")
    logger.info("Written by {}", AUTHOR)
    logger.info("Paper        : {}", paper_mode)
    logger.info("Market       : {} | Leverage: {}x (cap {})", market_type, leverage, cap)
    logger.info("Strategy     : {} | Risk: {}", strategy_name, risk_profile)
    logger.info("Symbol       : {} | {}", symbol, timeframe)
    if leverage > 1:
        logger.warning("LEVERAGE ON – losses amplify. Paper liquidation guard active.")
    logger.info("=" * 60)

    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet and not paper_mode,
        paper_mode=paper_mode,
    )

    trading_bot = TradingBot(client=client, state=state, config=cfg, poll_interval=45)
    threading.Thread(
        target=run_trading_loop, args=(trading_bot,), daemon=True, name="TradingEngine"
    ).start()

    tg_app = build_telegram_app(telegram_token, state, client=client)

    async def post_init(app):
        app.create_task(notification_worker(app, state))
        # One-time startup ping to allowed users
        from src.telegram.handlers import _allowed_users

        for uid in _allowed_users():
            try:
                await app.bot.send_message(
                    chat_id=uid,
                    text=(
                        f"🤖 *Bot online*\n"
                        f"Written by {AUTHOR}\n"
                        f"Paper: `{paper_mode}` | `{market_type}` | `{leverage}x`\n"
                        f"Send /start"
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    tg_app.post_init = post_init

    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(drop_pending_updates=True)

    try:
        while not state.shutdown_requested:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        state.shutdown_requested = True

    await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()
    logger.info("Shutdown complete – {}", AUTHOR)


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
