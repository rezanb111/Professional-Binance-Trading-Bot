"""CCXT Binance client wrapper with safety defaults."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import ccxt
from loguru import logger


class BinanceClient:
    """Thin, opinionated wrapper around ccxt.binance."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        dry_run: bool = True,
    ):
        self.dry_run = dry_run
        self.testnet = testnet

        config: Dict[str, Any] = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
            },
        }

        self.exchange = ccxt.binance(config)

        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("Connected to Binance SPOT TESTNET")
        else:
            logger.warning("Connected to Binance LIVE – real money at risk")

        # Load markets once
        self.exchange.load_markets()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
    ) -> List[List]:
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_balance(self) -> dict:
        return self.exchange.fetch_balance()

    def fetch_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def create_market_buy(
        self,
        symbol: str,
        amount: float,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        if self.dry_run:
            logger.info("[DRY-RUN] MARKET BUY {} amount={:.8f}", symbol, amount)
            return {"id": "dry-run-buy", "symbol": symbol, "side": "buy", "amount": amount}

        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side="buy",
                amount=amount,
                params=params or {},
            )
            logger.success("BUY order placed | {}", order.get("id"))
            return order
        except Exception as e:
            logger.error("Buy order failed: {}", e)
            return None

    def create_market_sell(
        self,
        symbol: str,
        amount: float,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        if self.dry_run:
            logger.info("[DRY-RUN] MARKET SELL {} amount={:.8f}", symbol, amount)
            return {"id": "dry-run-sell", "symbol": symbol, "side": "sell", "amount": amount}

        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side="sell",
                amount=amount,
                params=params or {},
            )
            logger.success("SELL order placed | {}", order.get("id"))
            return order
        except Exception as e:
            logger.error("Sell order failed: {}", e)
            return None

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        return float(self.exchange.amount_to_precision(symbol, amount))

    def price_to_precision(self, symbol: str, price: float) -> float:
        return float(self.exchange.price_to_precision(symbol, price))
