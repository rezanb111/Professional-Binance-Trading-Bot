"""Modern Telegram keyboards using Bot API 9.4 colored buttons + optional premium icons."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Optional premium custom emoji IDs (work if bot owner has Telegram Premium)
# These are well-known public IDs; replace with your own if needed.
EMOJI = {
    "play": "5237699328843200968",      # play / start style
    "stop": "5237699328843200968",
    "chart": "5379748062124056162",
    "analyze": "5379748062124056162",
    "money": "5379748062124056162",
    "warning": "5447644880824181073",
    "check": "5206607081334906820",
    "cross": "5210952531676504517",
}


def _btn(
    text: str,
    callback_data: str,
    style: str | None = None,
    icon_id: str | None = None,
) -> InlineKeyboardButton:
    """
    Create an InlineKeyboardButton with optional color style (Bot API 9.4+).

    style:
        - "primary"  → blue
        - "success"  → green
        - "danger"   → red
    icon_custom_emoji_id works when the bot owner has Telegram Premium.
    """
    kwargs = {
        "text": text,
        "callback_data": callback_data,
    }
    if style:
        kwargs["style"] = style
    if icon_id:
        kwargs["icon_custom_emoji_id"] = icon_id
    return InlineKeyboardButton(**kwargs)


def main_keyboard() -> InlineKeyboardMarkup:
    """Primary control panel with colored buttons."""
    keyboard = [
        [
            _btn("▶️ Start Trading", "cmd_start", style="success"),
            _btn("⏹ Stop Trading", "cmd_stop", style="danger"),
        ],
        [
            _btn("📊 Status", "cmd_status", style="primary"),
            _btn("📈 Analyze", "cmd_analyze", style="primary"),
            _btn("🖼 Chart", "cmd_chart", style="primary"),
        ],
        [
            _btn("🟢 Low Risk", "risk_low", style="success"),
            _btn("🟡 Medium", "risk_medium", style="primary"),
            _btn("🔴 High Risk", "risk_high", style="danger"),
        ],
        [
            _btn("❌ Close Position", "cmd_close", style="danger"),
            _btn("🧠 Strategies", "cmd_strategies", style="primary"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def strategies_keyboard() -> InlineKeyboardMarkup:
    """Quick strategy switcher."""
    strategies = [
        ("EMA + RSI", "strat_ema_rsi"),
        ("MACD", "strat_macd"),
        ("Bollinger", "strat_bollinger"),
        ("Supertrend", "strat_supertrend"),
        ("Breakout", "strat_breakout"),
        ("RSI Reversion", "strat_rsi_reversion"),
        ("Ichimoku", "strat_ichimoku"),
    ]
    rows = []
    row = []
    for i, (label, data) in enumerate(strategies):
        row.append(_btn(label, data, style="primary"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("⬅️ Back to Panel", "cmd_status", style="primary")])
    return InlineKeyboardMarkup(rows)
