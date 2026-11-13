"""Telegram handlers – written for bot by @shibainuo."""

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

AUTHOR = "@shibainuo"
ALLOWED_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}
LEV_CAPS = {"low": 2, "medium": 3, "high": 5}


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
    lev = s.get("leverage") or 1
    mtype = s.get("market_type") or "spot"

    lines = [
        f"🤖 *Professional Binance Bot*",
        f"_Written by {AUTHOR}_",
        "",
        f"Status: {status_emoji}",
        f"Mode: `{mode}` | `{mtype}` | `{lev}x`",
        f"Strategy: `{s['strategy_name']}` | Risk: `{s['risk_profile'].upper()}`",
        f"Pair: `{s['symbol']}` | TF: `{s['timeframe']}`",
        "",
        f"💰 Equity: `{s['equity']:.2f}` USDT ({ret:+.2f} / {ret_pct:+.2f}%)",
        f"Cash: `{s['paper_cash']:.2f}` | DD: `{s.get('max_drawdown_pct', 0)*100:.1f}%`",
        f"Price: `{s['last_price']:.2f}` | Signal: `{s['last_signal']}` ({s.get('last_signal_score', 0)})",
        f"Trades: `{s['trades_today']}` (W{s['wins_today']}/L{s['losses_today']})",
        f"Realized: `{s['realized_pnl_today']:+.2f}`",
    ]

    if upnl is not None:
        lines.append(f"Unrealized: `{upnl:+.2f}` USDT")

    if pos:
        lines += [
            "",
            "*Position*",
            f"{pos['side'].upper()} `{pos['quantity']:.6f}` @ `{pos['entry_price']:.2f}`",
            f"Lev `{pos.get('leverage', 1)}x` | SL `{pos['stop_price'] or '—'}` | TP `{pos['take_profit'] or '—'}`",
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
        f"🤖 *Professional Binance Trading Bot*\n"
        f"*Written by {AUTHOR}*\n\n"
        f"🧪 Paper: *${state.paper_start_balance:.0f}* virtual · **real** Binance prices\n"
        f"Market: `{state.market_type}` · Leverage: `{state.leverage}x`\n\n"
    )
    await update.message.reply_text(
        intro + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    text = f"""
*Written by {AUTHOR}*

/start /status /balance /stats
/start_bot /stop_bot
/risk low|medium|high
/strategy /strategies
/symbol BTC/USDT
/timeframe 15m|1h|4h
/market spot|future
/leverage 1-5
/analyze /chart /close
/reset_paper
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
        f"💰 Equity: `{s['equity']:.2f}`\nCash: `{s['paper_cash']:.2f}`",
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
        f"*Performance* · _{AUTHOR}_",
        f"Start `{s['paper_start_balance']:.2f}` → `{s['equity']:.2f}`",
        f"Return `{ret:+.2f}` | WR `{wr:.1f}%`",
        f"Trades `{s['trades_today']}` | Realized `{s['realized_pnl_today']:+.2f}`",
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
        await update.message.reply_text("Close position first: /close")
        return
    amount = float(os.getenv("PAPER_BALANCE", "1000"))
    state.reset_paper(amount)
    await update.message.reply_text(
        f"🔄 Paper reset to *${amount:.0f}*",
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
    await update.message.reply_text("▶️ *ENABLED*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    state.update(trading_enabled=False)
    await update.message.reply_text("⏹ *DISABLED*", parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args or args[0].lower() not in ("low", "medium", "high"):
        await update.message.reply_text("Usage: /risk <low|medium|high>")
        return
    profile = args[0].lower()
    state.update(risk_profile=profile)
    # re-cap leverage
    cap = LEV_CAPS.get(profile, 3)
    if state.leverage > cap:
        state.update(leverage=cap)
    await update.message.reply_text(
        f"⚙️ Risk *{profile.upper()}* (lev cap {cap}x)",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


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
    await update.message.reply_text(
        f"🧠 *{args[0].lower()}*", parse_mode="Markdown", reply_markup=main_keyboard()
    )


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
    await update.message.reply_text(f"📌 *{symbol}*", parse_mode="Markdown", reply_markup=main_keyboard())


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
    await update.message.reply_text(
        f"⏱ *{args[0].lower()}*", parse_mode="Markdown", reply_markup=main_keyboard()
    )


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args or args[0].lower() not in ("spot", "future"):
        await update.message.reply_text("Usage: /market spot|future")
        return
    if state.position:
        await update.message.reply_text("Close position first: /close")
        return
    m = args[0].lower()
    state.update(market_type=m)
    if m == "spot":
        state.update(leverage=1)
    await update.message.reply_text(
        f"📈 Market → *{m}*" + (" (leverage reset to 1x)" if m == "spot" else ""),
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def cmd_leverage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await unauthorized(update)
        return
    state: BotState = context.bot_data["state"]
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /leverage 1-5  (only with /market future)")
        return
    try:
        lev = int(args[0])
    except ValueError:
        await update.message.reply_text("Leverage must be an integer")
        return
    if state.market_type != "future":
        await update.message.reply_text("Set `/market future` first. Spot is always 1x.", parse_mode="Markdown")
        return
    if state.position:
        await update.message.reply_text("Close position first: /close")
        return
    cap = LEV_CAPS.get(state.risk_profile, 3)
    lev = max(1, min(lev, cap))
    state.update(leverage=lev)
    await update.message.reply_text(
        f"⚙️ Leverage → *{lev}x* (cap {cap}x for {state.risk_profile})",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


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
            f"*Analysis* `{state.symbol}` `{state.timeframe}`\n"
            f"_{AUTHOR}_\n\n"
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
            caption=f"{state.symbol} · {state.timeframe}\nWritten by {AUTHOR}",
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
        await query.edit_message_text(
            "▶️ ENABLED\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard()
        )
    elif data == "cmd_stop":
        state.update(trading_enabled=False)
        await query.edit_message_text(
            "⏹ DISABLED\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard()
        )
    elif data == "cmd_status":
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data.startswith("risk_"):
        profile = data.replace("risk_", "")
        state.update(risk_profile=profile)
        cap = LEV_CAPS.get(profile, 3)
        if state.leverage > cap:
            state.update(leverage=cap)
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    elif data == "cmd_close":
        state.update(force_close=True)
        await query.edit_message_text(
            "📤 Close requested\n\n" + status_text(state), parse_mode="Markdown", reply_markup=main_keyboard()
        )
    elif data == "cmd_strategies":
        available = list_strategies()
        lines = ["*Strategies*"] + [f"• `{n}` – {d}" for n, d in available.items()]
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=strategies_keyboard())
    elif data.startswith("strat_"):
        state.update(strategy_name=data.replace("strat_", ""))
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
    else:
        await query.edit_message_text(status_text(state), parse_mode="Markdown", reply_markup=main_keyboard())
