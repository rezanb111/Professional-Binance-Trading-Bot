"""Main trading bot orchestration."""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd
from loguru import logger

from src.exchange.client import BinanceClient
from src.risk.manager import RiskManager
from src.strategy.ema_rsi import EmaRsiStrategy


class TradingBot:
    """Core trading loop."""

    def __init__(
        self,
        client: BinanceClient,
        strategy: EmaRsiStrategy,
        risk_manager: RiskManager,
        symbol: str,
        timeframe: str,
        poll_interval: int = 60,
    ):
        self.client = client
        self.strategy = strategy
        self.risk = risk_manager
        self.symbol = symbol
        self.timeframe = timeframe
        self.poll_interval = poll_interval

        self.position_qty: float = 0.0
        self.entry_price: Optional[float] = None
        self.running = False

    def _get_equity(self) -> float:
        balance = self.client.fetch_balance()
        # Prefer USDT free + used
        usdt = balance.get("USDT", {})
        total = float(usdt.get("total", 0) or 0)
        return total

    def _fetch_dataframe(self) -> pd.DataFrame:
        ohlcv = self.client.fetch_ohlcv(self.symbol, self.timeframe, limit=150)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def _open_long(self, df: pd.DataFrame) -> None:
        if self.position_qty > 0:
            return

        equity = self._get_equity()
        self.risk.update_equity(equity)

        if self.risk.is_halted:
            logger.warning("Trading halted: {}", self.risk.halt_reason)
            return

        last = df.iloc[-1]
        atr = last.get("atr")
        if pd.isna(atr) or atr <= 0:
            logger.warning("ATR not available – skipping entry")
            return

        entry_price = float(last["close"])
        size_result = self.risk.calculate_position_size(equity, entry_price, float(atr))

        if not size_result:
            return

        qty = self.client.amount_to_precision(self.symbol, size_result.quantity)
        if qty <= 0:
            return

        order = self.client.create_market_buy(self.symbol, qty)
        if order:
            self.position_qty = qty
            self.entry_price = entry_price
            logger.success(
                "Opened LONG | qty={:.6f} | entry≈{:.2f} | stop≈{:.2f} | risk≈{:.2f} USDT",
                qty,
                entry_price,
                size_result.stop_price,
                size_result.risk_amount,
            )

    def _close_position(self) -> None:
        if self.position_qty <= 0:
            return

        order = self.client.create_market_sell(self.symbol, self.position_qty)
        if order:
            logger.success("Closed position | qty={:.6f}", self.position_qty)
            self.position_qty = 0.0
            self.entry_price = None

    def run(self) -> None:
        logger.info(
            "Bot started | symbol={} | timeframe={} | dry_run={}",
            self.symbol,
            self.timeframe,
            self.client.dry_run,
        )
        self.running = True

        while self.running:
            try:
                equity = self._get_equity()
                self.risk.update_equity(equity)

                if self.risk.is_halted:
                    logger.critical("Circuit breaker active – stopping bot")
                    break

                df = self._fetch_dataframe()
                signal = self.strategy.generate_signal(df)

                logger.debug(
                    "Signal={} | position_qty={:.6f} | equity={:.2f}",
                    signal,
                    self.position_qty,
                    equity,
                )

                if signal == "long" and self.position_qty == 0:
                    self._open_long(df)
                elif signal == "exit" and self.position_qty > 0:
                    self._close_position()

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt – shutting down")
                break
            except Exception as e:
                logger.exception("Error in main loop: {}", e)

            time.sleep(self.poll_interval)

        # Graceful exit – close open position if any (optional)
        # self._close_position()
        logger.info("Bot stopped")
