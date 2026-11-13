#!/usr/bin/env python3
"""
Professional Binance Trading Bot – Multi-Strategy + Full Telegram Control

Educational / research use only.
Never risk capital you cannot afford to lose.
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

# Ensure all strategies are registered
import src.strategy  # noqa: F401


def load_config() -> dict:
    with open(ROOT / "config" / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_trading_loop(bot: TradingBot) -> None:
    bot.run()


async def main_async() -> None:
    load_dotenv()
    setup_logger(os.getenv("LOG_LEVEL", "INFO"))

    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() in ("1", "true", "yes")
    dry_run = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
    risk_profile = os.getenv("RISK_PROFILE", "medium").lower()
    strategy_name = os.getenv("STRATEGY", "ema_rsi").lower()
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1h")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")

    if not api_key or not api_secret:
        logger.error("BINANCE_API_KEY / SECRET required")
        sys.exit(1)
    if not telegram_token or not allowed_users.strip():
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS required")
        sys.exit(1)
    if risk_profile not in ("low", "medium", "high"):
        logger.error("RISK_PROFILE must be low|medium|high")
        sys.exit(1)

    cfg = load_config()

    state = BotState(
        risk_profile=risk_profile,
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        dry_run=dry_run,
        testnet=testnet,
        trading_enabled=False,
    )

    logger.info("=" * 60)
    logger.info("Professional Binance Bot | Multi-Strategy + Telegram")
    logger.info("Strategy     : {}", strategy_name)
    logger.info("Risk Profile : {}", risk_profile.upper())
    logger.info("Symbol       : {} | {}", symbol, timeframe)
    logger.info("Testnet      : {} | Dry-Run: {}", testnet, dry_run)
    logger.info("=" * 60)

    client = BinanceClient(api_key, api_secret, testnet=testnet, dry_run=dry_run)

    trading_bot = TradingBot(client=client, state=state, config=cfg, poll_interval=45)
    t = threading.Thread(target=run_trading_loop, args=(trading_bot,), daemon=True, name="TradingEngine")
    t.start()

    tg_app = build_telegram_app(telegram_token, state, client=client)

    async def post_init(app):
        app.create_task(notification_worker(app, state))

    tg_app.post_init = post_init

    logger.info("Telegram control panel starting... Send /start to your bot")

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
    logger.info("Shutdown complete")


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
