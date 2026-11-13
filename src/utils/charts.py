"""Generate price + indicator charts for Telegram."""

from __future__ import annotations

import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.indicators.technical import add_all_indicators


def create_chart(df: pd.DataFrame, symbol: str, timeframe: str) -> Optional[bytes]:
    """Return PNG bytes of a multi-panel chart."""
    if df.empty or len(df) < 30:
        return None

    df = add_all_indicators(df).tail(80).copy()

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [3, 1, 1]}, sharex=True)
    fig.suptitle(f"{symbol} · {timeframe}", fontsize=13, fontweight="bold")

    ax1, ax2, ax3 = axes

    # Price + EMAs + Bollinger
    ax1.plot(df.index, df["close"], label="Close", color="#1f77b4", linewidth=1.4)
    ax1.plot(df.index, df["ema_9"], label="EMA 9", color="orange", alpha=0.8, linewidth=1)
    ax1.plot(df.index, df["ema_21"], label="EMA 21", color="green", alpha=0.8, linewidth=1)
    ax1.fill_between(df.index, df["bb_low"], df["bb_high"], color="gray", alpha=0.15, label="Bollinger")
    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2.plot(df.index, df["rsi"], color="purple", linewidth=1.2)
    ax2.axhline(70, color="red", linestyle="--", alpha=0.6)
    ax2.axhline(30, color="green", linestyle="--", alpha=0.6)
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)

    # MACD
    ax3.plot(df.index, df["macd"], label="MACD", color="blue", linewidth=1)
    ax3.plot(df.index, df["macd_signal"], label="Signal", color="orange", linewidth=1)
    ax3.bar(df.index, df["macd_hist"], label="Hist", color="gray", alpha=0.5)
    ax3.set_ylabel("MACD")
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
