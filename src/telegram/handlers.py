"""Telegram command handlers – full control panel + analysis + charts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes

from src.core.state import BotState
from src.indicators.technical import add_all_indicators, market_summary
from src.strategy import list_strategies
from src.utils.charts import create_chart


def _allowed_users() -> List[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def is_authorized(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    allowed = _allowed_users()
    return bool(allowed) and user.id in allowed


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
        f"Strategy: `{s['strategy_name']}`",
        f"Risk: `{s['risk_profile'].upper()}`",
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
            InlineKeyboardButton("📈 Analyze", callback_data="cmd_analyze"),
            InlineKeyboardButton("🖼 Chart", callback_data="cmd_chart"),
        ],
        [
            InlineKeyboardButton("🟢 Low", callback_data="risk_low"),
            InlineKeyboardButton("🟡 Med", callback_data="risk_medium"),
            InlineKeyboardButton("🔴 High", callback_data="risk_high"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="cmd_close"),
            InlineKeyboardButton("📋 Strategies", callback_data="cmd_strategies"),
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
        "Full remote control + multi-strategy + analysis.\n\n"
        + status_text(state)
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    text = """
*Commands*

/start – Control panel
/status – Live status
/balance – Equity
/start\_bot – Enable trading
/stop\_bot – Disable trading
/risk <low|medium|high>
/strategy <name> – Switch strategy
/strategies – List all strategies
/analyze – Technical analysis summary
/chart – Send price chart with indicators
/close – Force close position
/help – This message

*Strategies available*
`ema_rsi` `macd` `bollinger` `supertrend` `breakout` `rsi_reversion` `ichimoku`
""".strip()
    await update.message.reply_text(text, parse_mode="Markdown")


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
        f"💰 *Equity*: `{state.equity:.2f} USDT`",
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
    state.add_notification("▶️ Trading ENABLED")
    await update.message.reply_text("▶️ Trading *ENABLED*", parse_mode="Markdown")


async def cmd_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=False)
    state.add_notification("⏹ Trading DISABLED")
    await update.message.reply_text("⏹ Trading *DISABLED*", parse_mode="Markdown")


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
    state.add_notification(f"⚙️ Risk → *{new_profile.upper()}*")
    await update.message.reply_text(f"⚙️ Risk set to *{new_profile.upper()}*", parse_mode="Markdown")


async def cmd_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    available = list_strategies()

    if not args or args[0].lower() not in available:
        lines = ["*Available strategies:*"]
        for name, desc in available.items():
            lines.append(f"• `{name}` – {desc}")
        lines.append("\nUsage: /strategy <name>")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    name = args[0].lower()
    state.update(strategy_name=name)
    state.add_notification(f"🧠 Strategy → `{name}`")
    await update.message.reply_text(f"🧠 Strategy switched to *{name}*", parse_mode="Markdown")


async def cmd_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    available = list_strategies()
    lines = ["*Available Strategies*"]
    for name, desc in available.items():
        lines.append(f"• `{name}`\n  _{desc}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(force_close=True)
    await update.message.reply_text("📤 Force close requested.")


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    state: BotState = context.bot_data["state"]
    client = context.bot_data.get("client")
    if not client:
        await update.message.reply_text("Exchange client not ready.")
        return

    await update.message.reply_text("⏳ Analyzing...")

    try:
        ohlcv = client.fetch_ohlcv(state.symbol, state.timeframe, limit=150)
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = add_all_indicators(df)
        summary = market_summary(df)

        if "error" in summary:
            await update.message.reply_text(summary["error"])
            return

        text = (
            f"*Technical Analysis* – `{state.symbol}` `{state.timeframe}`\n\n"
            f"Price: `{summary['price']:.2f}`\n"
            f"Trend: *{summary['trend']}*\n"
            f"Trend Strength (ADX): `{summary['adx']:.1f}` ({summary['trend_strength']})\n"
            f"RSI(14): `{summary['rsi']:.1f}` ({summary['rsi_state']})\n"
            f"ATR: `{summary['atr']:.2f}`\n"
            f"Bollinger: {summary['bb_position']}\n"
            f"Volume Ratio: `{summary['volume_ratio']:.2f}`\n"
            f"MACD Hist: `{summary['macd_hist']:.4f}`\n"
            f"EMA9 / 21 / 50: `{summary['ema_9']:.1f}` / `{summary['ema_21']:.1f}` / `{summary['ema_50']:.1f}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        logger.exception("Analyze failed")
        await update.message.reply_text(f"Analyze error: {e}")


async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return

    state: BotState = context.bot_data["state"]
    client = context.bot_data.get("client")
    if not client:
        await update.message.reply_text("Exchange client not ready.")
        return

    await update.message.reply_text("⏳ Generating chart...")

    try:
        ohlcv = client.fetch_ohlcv(state.symbol, state.timeframe, limit=120)
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        png = create_chart(df, state.symbol, state.timeframe)
        if not png:
            await update.message.reply_text("Not enough data for chart.")
            return

        await update.message.reply_photo(
            photo=InputFile(png, filename=f"{state.symbol.replace('/', '_')}_chart.png"),
            caption=f"{state.symbol} · {state.timeframe}",
        )
    except Exception as e:
        logger.exception("Chart failed")
        await update.message.reply_text(f"Chart error: {e}")


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
        await query.edit_message_text("▶️ Trading *ENABLED*\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_stop":
        state.update(trading_enabled=False)
        await query.edit_message_text("⏹ Trading *DISABLED*\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_status":
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data.startswith("risk_"):
        profile = data.replace("risk_", "")
        state.update(risk_profile=profile)
        await query.edit_message_text(
            f"⚙️ Risk → *{profile.upper()}*\n\n" + status_text(state),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )

    elif data == "cmd_close":
        state.update(force_close=True)
        await query.edit_message_text("📤 Close requested.\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_strategies":
        available = list_strategies()
        lines = ["*Strategies*"]
        for name, desc in available.items():
            lines.append(f"• `{name}` – {desc}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())

    elif data == "cmd_analyze":
        await query.edit_message_text("Use /analyze command for full technical analysis.", reply_markup=main_keyboard())

    elif data == "cmd_chart":
        await query.edit_message_text("Use /chart command to generate and receive the chart.", reply_markup=main_keyboard())
