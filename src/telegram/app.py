"""Telegram app – bot by @shibainuo."""

from __future__ import annotations

import asyncio
from loguru import logger
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.core.state import BotState
from src.telegram.handlers import (
    button_handler,
    cmd_analyze,
    cmd_balance,
    cmd_chart,
    cmd_close,
    cmd_help,
    cmd_leverage,
    cmd_market,
    cmd_reset_paper,
    cmd_risk,
    cmd_start,
    cmd_start_bot,
    cmd_stats,
    cmd_status,
    cmd_stop_bot,
    cmd_strategies,
    cmd_strategy,
    cmd_symbol,
    cmd_timeframe,
)


def build_telegram_app(token: str, state: BotState, client=None) -> Application:
    app = Application.builder().token(token).build()
    app.bot_data["state"] = state
    if client:
        app.bot_data["client"] = client

    handlers = [
        ("start", cmd_start),
        ("help", cmd_help),
        ("status", cmd_status),
        ("balance", cmd_balance),
        ("stats", cmd_stats),
        ("start_bot", cmd_start_bot),
        ("stop_bot", cmd_stop_bot),
        ("risk", cmd_risk),
        ("strategy", cmd_strategy),
        ("strategies", cmd_strategies),
        ("symbol", cmd_symbol),
        ("timeframe", cmd_timeframe),
        ("market", cmd_market),
        ("leverage", cmd_leverage),
        ("close", cmd_close),
        ("analyze", cmd_analyze),
        ("chart", cmd_chart),
        ("reset_paper", cmd_reset_paper),
    ]
    for name, fn in handlers:
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(button_handler))
    return app


async def notification_worker(app: Application, state: BotState, interval: float = 3.0) -> None:
    from src.telegram.handlers import _allowed_users

    allowed = _allowed_users()
    if not allowed:
        return

    while not state.shutdown_requested:
        for note in state.pop_notifications():
            for uid in allowed:
                try:
                    await app.bot.send_message(chat_id=uid, text=note, parse_mode="Markdown")
                except Exception as e:
                    logger.warning("notify failed: {}", e)
        await asyncio.sleep(interval)
