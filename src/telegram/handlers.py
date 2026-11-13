"""Telegram command handlers – full control panel."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.core.state import BotState


def _allowed_users() -> List[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def is_authorized(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    allowed = _allowed_users()
    if not allowed:
        # If no users configured, deny everyone for safety
        return False
    return user.id in allowed


async def unauthorized(update: Update) -> None:
    if update.message:
        await update.message.reply_text("⛔ Unauthorized. This bot is private.")


def status_text(state: BotState) -> str:
    s = state.snapshot()
    pos = s.get("position")

    status_emoji = "🟢 RUNNING" if s["trading_enabled"] else "🔴 STOPPED"
    mode = "🧪 DRY-RUN" if s["dry_run"] else ("🔵 TESTNET" if s["testnet"] else "🔴 LIVE")

    lines = [
        f"*Professional Binance Bot*",
        f"",
        f"Status: {status_emoji}",
        f"Mode: `{mode}`",
        f"Risk Profile: `{s['risk_profile'].upper()}`",
        f"Symbol: `{s['symbol']}` | TF: `{s['timeframe']}`",
        f"",
        f"Equity: `{s['equity']:.2f} USDT`",
        f"Last Price: `{s['last_price']:.2f}`",
        f"Last Signal: `{s['last_signal']}`",
        f"Trades today: `{s['trades_today']}`",
        f"PnL today: `{s['realized_pnl_today']:+.2f} USDT`",
    ]

    if pos:
        lines += [
            f"",
            f"*Open Position*",
            f"Side: `{pos['side'].upper()}`",
            f"Qty: `{pos['quantity']:.6f}`",
            f"Entry: `{pos['entry_price']:.2f}`",
            f"Stop: `{pos['stop_price'] or '—'}`",
            f"TP: `{pos['take_profit'] or '—'}`",
        ]
    else:
        lines.append("\nNo open position")

    if s["last_update"]:
        lines.append(f"\n_Updated: {s['last_update']}_")

    return "\n".join(lines)


def main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start", callback_data="cmd_start"),
            InlineKeyboardButton("⏹ Stop", callback_data="cmd_stop"),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="cmd_status"),
            InlineKeyboardButton("💰 Balance", callback_data="cmd_balance"),
        ],
        [
            InlineKeyboardButton("🟢 Low", callback_data="risk_low"),
            InlineKeyboardButton("🟡 Medium", callback_data="risk_medium"),
            InlineKeyboardButton("🔴 High", callback_data="risk_high"),
        ],
        [
            InlineKeyboardButton("❌ Close Position", callback_data="cmd_close"),
            InlineKeyboardButton("ℹ️ Help", callback_data="cmd_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    state: BotState = context.bot_data["state"]
    text = (
        "🤖 *Professional Binance Trading Bot*\n\n"
        "Full remote control panel ready.\n"
        "Use the buttons below or commands.\n\n"
        + status_text(state)
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    help_text = """
*Available Commands*

/start – Open control panel
/status – Full status
/balance – Account equity
/start\_bot – Enable trading loop
/stop\_bot – Disable trading loop
/risk <low|medium|high> – Change risk profile
/close – Force close open position
/help – This message

*Inline Buttons*
Use the keyboard for quick actions.

⚠️ Only authorized users can control this bot.
""".strip()
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    await update.message.reply_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    await update.message.reply_text(
        f"💰 *Equity*: `{state.equity:.2f} USDT`\n"
        f"Mode: `{'DRY-RUN' if state.dry_run else ('TESTNET' if state.testnet else 'LIVE')}`",
        parse_mode="Markdown",
    )


async def cmd_start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=True)
    if state.started_at is None:
        state.started_at = datetime.now(timezone.utc)
    state.add_notification("▶️ Trading ENABLED via Telegram")
    await update.message.reply_text("▶️ Trading loop *ENABLED*", parse_mode="Markdown")


async def cmd_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=False)
    state.add_notification("⏹ Trading DISABLED via Telegram")
    await update.message.reply_text("⏹ Trading loop *DISABLED*", parse_mode="Markdown")


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args or args[0].lower() not in ("low", "medium", "high"):
        await update.message.reply_text("Usage: /risk <low|medium|high>")
        return

    new_profile = args[0].lower()
    state.update(risk_profile=new_profile)
    state.add_notification(f"⚙️ Risk profile changed to *{new_profile.upper()}*")
    await update.message.reply_text(
        f"⚙️ Risk profile set to *{new_profile.upper()}*\n"
        "It will apply on the next strategy cycle.",
        parse_mode="Markdown",
    )


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    # Signal the trading loop to close
    state.add_notification("FORCE_CLOSE")
    await update.message.reply_text("📤 Close request sent. Position will be closed on next cycle.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if not is_authorized(update):
        await query.edit_message_text("⛔ Unauthorized")
        return

    state: BotState = context.bot_data["state"]
    data = query.data or ""

    if data == "cmd_start":
        state.update(trading_enabled=True)
        if state.started_at is None:
            state.started_at = datetime.now(timezone.utc)
        state.add_notification("▶️ Trading ENABLED via button")
        await query.edit_message_text("▶️ Trading *ENABLED*\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_stop":
        state.update(trading_enabled=False)
        state.add_notification("⏹ Trading DISABLED via button")
        await query.edit_message_text("⏹ Trading *DISABLED*\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_status":
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_balance":
        await query.edit_message_text(
            f"💰 Equity: `{state.equity:.2f} USDT`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif data.startswith("risk_"):
        profile = data.replace("risk_", "")
        state.update(risk_profile=profile)
        state.add_notification(f"⚙️ Risk → {profile.upper()}")
        await query.edit_message_text(
            f"⚙️ Risk profile → *{profile.upper()}*\n\n" + status_text(state),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif data == "cmd_close":
        state.add_notification("FORCE_CLOSE")
        await query.edit_message_text("📤 Close request sent.\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_help":
        await query.edit_message_text(
            "Use /help for full command list.\n\nButtons provide quick control.",
            reply_markup=main_keyboard(),
        )
