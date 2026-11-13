"""Telegram application setup and notification worker."""

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

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("start_bot", cmd_start_bot))
    app.add_handler(CommandHandler("stop_bot", cmd_stop_bot))
    app.add_handler(CommandHandler("risk", cmd_risk))
    app.add_handler(CommandHandler("strategy", cmd_strategy))
    app.add_handler(CommandHandler("strategies", cmd_strategies))
    app.add_handler(CommandHandler("symbol", cmd_symbol))
    app.add_handler(CommandHandler("timeframe", cmd_timeframe))
    app.add_handler(CommandHandler("close", cmd_close))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("chart", cmd_chart))
    app.add_handler(CallbackQueryHandler(button_handler))

    return app


async def notification_worker(app: Application, state: BotState, interval: float = 3.0) -> None:
    from src.telegram.handlers import _allowed_users

    allowed = _allowed_users()
    if not allowed:
        logger.warning("No TELEGRAM_ALLOWED_USERS – notifications disabled")
        return

    while not state.shutdown_requested:
        notes = state.pop_notifications()
        for note in notes:
            for user_id in allowed:
                try:
                    await app.bot.send_message(chat_id=user_id, text=note, parse_mode="Markdown")
                except Exception as e:
                    logger.warning("TG notify failed to {}: {}", user_id, e)
        await asyncio.sleep(interval)
