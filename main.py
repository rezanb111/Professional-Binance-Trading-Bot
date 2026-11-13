#!/usr/bin/env python3
"""
Professional Binance Trading Bot – Entry Point

Educational / research use only.
Never risk capital you cannot afford to lose.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.bot import TradingBot
from src.exchange.client import BinanceClient
from src.risk.manager import RiskManager
from src.strategy.ema_rsi import EmaRsiStrategy
from src.utils.logger import setup_logger


def load_config() -> dict:
    config_path = ROOT / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    load_dotenv()

    # ---- Logging ----
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logger(log_level)

    # ---- Environment ----
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() in ("1", "true", "yes")
    dry_run = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
    risk_profile_name = os.getenv("RISK_PROFILE", "medium").lower()
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1h")

    if not api_key or not api_secret:
        logger.error("BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env")
        sys.exit(1)

    if risk_profile_name not in ("low", "medium", "high"):
        logger.error("RISK_PROFILE must be one of: low, medium, high")
        sys.exit(1)

    # ---- Config ----
    cfg = load_config()
    profile = cfg["risk_profiles"][risk_profile_name]
    circuit = cfg.get("circuit_breaker", {})

    logger.info("=" * 60)
    logger.info("Professional Binance Trading Bot")
    logger.info("Risk Profile : {}", risk_profile_name.upper())
    logger.info("Symbol       : {}", symbol)
    logger.info("Timeframe    : {}", timeframe)
    logger.info("Testnet      : {}", testnet)
    logger.info("Dry-Run      : {}", dry_run)
    logger.info("Risk/Trade   : {:.2%}", profile["risk_per_trade"])
    logger.info("=" * 60)

    if not dry_run and not testnet:
        logger.warning("!!! LIVE TRADING WITH REAL MONEY ENABLED !!!")
        logger.warning("Press Ctrl+C within 10 seconds to abort...")
        import time
        time.sleep(10)

    # ---- Components ----
    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        dry_run=dry_run,
    )

    strategy = EmaRsiStrategy(params=profile)
    risk_manager = RiskManager(profile=profile, circuit_breaker=circuit)

    bot = TradingBot(
        client=client,
        strategy=strategy,
        risk_manager=risk_manager,
        symbol=symbol,
        timeframe=timeframe,
        poll_interval=45,  # seconds
    )

    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")


if __name__ == "__main__":
    main()
