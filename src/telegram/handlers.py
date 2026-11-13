"""Telegram handlers including paper reset."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from loguru import logger
from telegram import Update, InputFile
from telegram.ext import ContextTypes

from src.core.journal import load_recent
from src.core.state import BotState
from src.indicators.technical import add_all_indicators, market_summary
from src.strategy import list_strategies
from src.telegram.keyboards import main_keyboard, strategies_keyboard
from src.utils.charts import create_chart

ALLOWED_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}


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
        await update.message.reply_text("⛔ Unauthorized.")


def status_text(state: BotState) -> str:
    s = state.snapshot()
    pos = s.get("position")
    upnl = s.get("unrealized_pnl")

    status_emoji = "🟢 RUNNING" if s["trading_enabled"] else "🔴 STOPPED"
    if s["paper_mode"]:
        mode = f"🧪 PAPER ${s['paper_start_balance']:.0f}"
    else:
        mode = "🔵 TESTNET" if s["testnet"] else "🔴 LIVE"

    ret = s["equity"] - s["paper_start_balance"]
    ret_pct = (ret / s["paper_start_balance"] * 100) if s["paper_start_balance"] else 0

    lines = [
        "🤖 *Professional Binance Trading Bot*",
        "",
        f"Status: {status_emoji}",
        f"Mode: `{mode}`",
        f"Strategy: `{s['strategy_name']}` | Risk: `{s['risk_profile'].upper()}`",
        f"Pair: `{s['symbol']}` | TF: `{s['timeframe']}`",
        "",
        f"💰 Equity: `{s['equity']:.2f}` USDT ({ret:+.2f} / {ret_pct:+.2f}%)",
        f"Cash: `{s['paper_cash']:.2f}` USDT",
        f"Price: `{s['last_price']:.2f}` | Signal: `{s['last_signal']}`",
        f"Trades: `{s['trades_today']}` (W{s['wins_today']}/L{s['losses_today']})",
        f"Realized PnL: `{s['realized_pnl_today']:+.2f}`",
    ]

    if upnl is not None:
        lines.append(f"Unrealized: `{upnl:+.2f}` USDT")

    if pos:
        lines += [
            "",
            "*Position*",
            f"{pos['side'].upper()} `{pos['quantity']:.6f}` @ `{pos['entry_price']:.2f}`",
            f"SL `{pos['stop_price'] or '—'}` | TP `{pos['take_profit'] or '—'}`",
        ]
    else:
        lines.append("\nNo open position")

    if s["last_update"]:
        lines.append(f"\n_{s['last_update']}_")

    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    intro = (
        "🧪 *Paper Trading Mode*\n"
        f"You start with *${state.paper_start_balance:.0f}* virtual USDT.\n"
        "Prices are **100% real** from Binance.\n"
        "No real money is used until you disable PAPER_MODE.\n\n"
    )
    await update.message.reply_text(
        intro + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    text = """
*Commands*
/start /status /balance /stats
/start_bot /stop_bot
/risk low|medium|high
/strategy <name> /strategies
/symbol BTC/USDT
/timeframe 15m|1h|4h
/analyze /chart /close
/reset_paper – reset virtual balance to $1000
/help
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
    s = state.snapshot()
    await update.message.reply_text(
        f"💰 Equity: `{s['equity']:.2f}` USDT\nCash: `{s['paper_cash']:.2f}`",
        parse_mode="Markdown",
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    s = state.snapshot()
    total = s["wins_today"] + s["losses_today"]
    wr = (s["wins_today"] / total * 100) if total else 0
    ret = s["equity"] - s["paper_start_balance"]

    lines = [
        "*Performance*",
        f"Start: `{s['paper_start_balance']:.2f}` → Equity: `{s['equity']:.2f}`",
        f"Return: `{ret:+.2f}` USDT",
        f"Trades: `{s['trades_today']}` | WR: `{wr:.1f}%`",
        f"Realized: `{s['realized_pnl_today']:+.2f}`",
    ]
    recent = load_recent(8)
    if recent:
        lines.append("\n*Journal*")
        for r in reversed(recent):
            lines.append(f"`{r.get('event')}` {r.get('symbol')} {r.get('pnl') or ''}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_reset_paper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    if state.position:
        await update.message.reply_text("Close open position first with /close")
        return
    amount = float(os.getenv("PAPER_BALANCE", "1000"))
    state.reset_paper(amount)
    state.add_notification(f"🔄 Paper balance reset to ${amount:.0f}")
    await update.message.reply_text(
        f"🔄 Paper account reset to *${amount:.0f}* USDT",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def cmd_start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=True)
    if state.started_at is None:
        state.started_at = datetime.now(timezone.utc)
    await update.message.reply_text("▶️ Trading *ENABLED*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=False)
    await update.message.reply_text("⏹ Trading *DISABLED*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args or args[0].lower() not in ("low", "medium", "high"):
        await update.message.reply_text("Usage: /risk <low|medium|high>")
        return
    state.update(risk_profile=args[0].lower())
    await update.message.reply_text(f"⚙️ Risk → *{args[0].upper()}*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    available = list_strategies()
    if not args or args[0].lower() not in available:
        lines = ["*Strategies*"] + [f"• `{n}` – {d}" for n, d in available.items()]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return
    state.update(strategy_name=args[0].lower())
    await update.message.reply_text(f"🧠 Strategy → *{args[0].lower()}*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    available = list_strategies()
    lines = ["*Strategies*"] + [f"• `{n}` – {d}" for n, d in available.items()]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=strategies_keyboard())


async def cmd_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /symbol BTC/USDT")
        return
    symbol = args[0].upper().replace("-", "/")
    if "/" not in symbol:
        symbol += "/USDT"
    state.update(symbol=symbol)
    await update.message.reply_text(f"📌 Symbol → *{symbol}*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args or args[0].lower() not in ALLOWED_TIMEFRAMES:
        await update.message.reply_text("Usage: /timeframe 1m|5m|15m|1h|4h|1d")
        return
    state.update(timeframe=args[0].lower())
    await update.message.reply_text(f"⏱ TF → *{args[0].lower()}*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(force_close=True)
    await update.message.reply_text("📤 Close requested.", reply_markup=main_keyboard())


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    client = context.bot_data.get("client")
    if not client:
        await update.message.reply_text("Client not ready")
        return
    msg = await update.message.reply_text("⏳ Analyzing...")
    try:
        import pandas as pd
        ohlcv = client.fetch_ohlcv(state.symbol, state.timeframe, limit=150)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = add_all_indicators(df)
        summary = market_summary(df)
        if "error" in summary:
            await msg.edit_text(summary["error"])
            return
        text = (
            f"*Analysis* `{state.symbol}` `{state.timeframe}`\n\n"
            f"Price `{summary['price']:.2f}`\n"
            f"Trend *{summary['trend']}* | ADX `{summary['adx']:.1f}`\n"
            f"RSI `{summary['rsi']:.1f}` ({summary['rsi_state']})\n"
            f"ATR `{summary['atr']:.2f}` | Vol `{summary['volume_ratio']:.2f}`\n"
            f"BB: {summary['bb_position']}\n"
            f"EMA 9/21/50: `{summary['ema_9']:.1f}` / `{summary['ema_21']:.1f}` / `{summary['ema_50']:.1f}`"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        await msg.edit_text(f"Error: {e}")


async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    client = context.bot_data.get("client")
    if not client:
        await update.message.reply_text("Client not ready")
        return
    status_msg = await update.message.reply_text("⏳ Chart...")
    try:
        import pandas as pd
        ohlcv = client.fetch_ohlcv(state.symbol, state.timeframe, limit=120)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        png = create_chart(df, state.symbol, state.timeframe)
        if not png:
            await status_msg.edit_text("Not enough data")
            return
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(png, filename="chart.png"),
            caption=f"{state.symbol} · {state.timeframe}",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        await status_msg.edit_text(f"Chart error: {e}")


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
        await query.edit_message_text("▶️ ENABLED\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data == "cmd_stop":
        state.update(trading_enabled=False)
        await query.edit_message_text("⏹ DISABLED\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data == "cmd_status":
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data.startswith("risk_"):
        state.update(risk_profile=data.replace("risk_", ""))
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data == "cmd_close":
        state.update(force_close=True)
        await query.edit_message_text("📤 Close requested\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data == "cmd_strategies":
        available = list_strategies()
        lines = ["*Strategies*"] + [f"• `{n}` – {d}" for n, d in available.items()]
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=strategies_keyboard())
    elif data.startswith("strat_"):
        state.update(strategy_name=data.replace("strat_", ""))
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    else:
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
