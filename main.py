#!/usr/bin/env python3
"""
Professional Binance Trading Bot – Full Telegram Control

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


def load_config() -> dict:
    config_path = ROOT / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_trading_loop(bot: TradingBot) -> None:
    """Run the blocking trading loop in a dedicated thread."""
    bot.run()


async def main_async() -> None:
    load_dotenv()

    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logger(log_level)

    # ---- Environment ----
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() in ("1", "true", "yes")
    dry_run = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
    risk_profile = os.getenv("RISK_PROFILE", "medium").lower()
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1h")

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")

    if not api_key or not api_secret:
        logger.error("BINANCE_API_KEY and BINANCE_API_SECRET must be set")
        sys.exit(1)

    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN must be set for control panel")
        sys.exit(1)

    if not allowed_users.strip():
        logger.error("TELEGRAM_ALLOWED_USERS must be set (your Telegram user ID)")
        sys.exit(1)

    if risk_profile not in ("low", "medium", "high"):
        logger.error("RISK_PROFILE must be low | medium | high")
        sys.exit(1)

    cfg = load_config()

    # ---- Shared State ----
    state = BotState(
        risk_profile=risk_profile,
        symbol=symbol,
        timeframe=timeframe,
        dry_run=dry_run,
        testnet=testnet,
        trading_enabled=False,  # start stopped – enable via Telegram
    )

    logger.info("=" * 60)
    logger.info("Professional Binance Trading Bot + Telegram Control")
    logger.info("Risk Profile : {}", risk_profile.upper())
    logger.info("Symbol       : {}", symbol)
    logger.info("Timeframe    : {}", timeframe)
    logger.info("Testnet      : {}", testnet)
    logger.info("Dry-Run      : {}", dry_run)
    logger.info("Telegram     : Enabled")
    logger.info("=" * 60)

    if not dry_run and not testnet:
        logger.warning("!!! LIVE TRADING WITH REAL MONEY ENABLED !!!")

    # ---- Exchange Client ----
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        dry_run=dry_run,
    )

    # ---- Trading Engine (background thread) ----
    trading_bot = TradingBot(
        client=client,
        state=state,
        config=cfg,
        poll_interval=45,
    )

    trading_thread = threading.Thread(
        target=run_trading_loop,
        args=(trading_bot,),
        name="TradingEngine",
        daemon=True,
    )
    trading_thread.start()

    # ---- Telegram Application ----
    tg_app = build_telegram_app(telegram_token, state)

    # Start notification worker
    async def post_init(app):
        app.create_task(notification_worker(app, state))

    tg_app.post_init = post_init

    logger.info("Telegram control panel starting...")
    logger.info("Send /start to your bot to open the control panel")

    # Run Telegram (blocking)
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(drop_pending_updates=True)

    # Keep alive until shutdown
    try:
        while not state.shutdown_requested:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
        state.shutdown_requested = True

    await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()
    logger.info("Bot fully stopped")


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
