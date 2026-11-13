"""CCXT Binance client – supports live, testnet, and pure paper (public market data)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import ccxt
from loguru import logger


class BinanceClient:
    """
    Binance wrapper.

    paper_mode=True  → never sends real orders; market data is still REAL from Binance.
    testnet=True     → Binance Spot Testnet (if keys provided)
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
        paper_mode: bool = True,
    ):
        self.paper_mode = paper_mode
        self.testnet = testnet and not paper_mode

        config: Dict[str, Any] = {
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True,
            },
        }

        # Keys only needed for real / testnet trading
        if api_key and api_secret and not paper_mode:
            config["apiKey"] = api_key
            config["secret"] = api_secret

        self.exchange = ccxt.binance(config)

        if self.testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("Connected to Binance SPOT TESTNET")
        elif paper_mode:
            # Public endpoints – real production prices, no orders
            logger.info("PAPER MODE – real Binance prices, virtual $ balance, no real orders")
        else:
            logger.warning("LIVE MODE – real money at risk")

        try:
            self.exchange.load_markets()
        except Exception as e:
            logger.warning("load_markets failed (will retry on first call): {}", e)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
    ) -> List[List]:
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def fetch_balance(self) -> dict:
        """Real balance only when not in paper mode."""
        if self.paper_mode:
            return {"USDT": {"free": 0, "used": 0, "total": 0}}
        return self.exchange.fetch_balance()

    def create_market_buy(
        self,
        symbol: str,
        amount: float,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        if self.paper_mode:
            ticker = self.fetch_ticker(symbol)
            price = float(ticker.get("last") or ticker.get("close") or 0)
            logger.info("[PAPER] BUY {} amount={:.8f} @ ≈{:.4f}", symbol, amount, price)
            return {
                "id": "paper-buy",
                "symbol": symbol,
                "side": "buy",
                "amount": amount,
                "price": price,
                "average": price,
                "status": "closed",
            }

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
        if self.paper_mode:
            ticker = self.fetch_ticker(symbol)
            price = float(ticker.get("last") or ticker.get("close") or 0)
            logger.info("[PAPER] SELL {} amount={:.8f} @ ≈{:.4f}", symbol, amount, price)
            return {
                "id": "paper-sell",
                "symbol": symbol,
                "side": "sell",
                "amount": amount,
                "price": price,
                "average": price,
                "status": "closed",
            }

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
        try:
            return float(self.exchange.amount_to_precision(symbol, amount))
        except Exception:
            return float(f"{amount:.6f}")

    def price_to_precision(self, symbol: str, price: float) -> float:
        try:
            return float(self.exchange.price_to_precision(symbol, price))
        except Exception:
            return float(f"{price:.4f}")
