"""Core 6: Tokenized US Stocks Agent - 7x24 Equities & Cross-Asset Hedging."""

from typing import Any, Dict
from bitget_skills_hub.tokenized_stocks.tools import (
    scan_tokenized_stocks,
    detect_after_hours_spread,
    execute_cross_asset_hedge
)
from src.core.memory import memory, LogLevel


class TokenizedStocksAgent:
    """Specialist sub-agent for 7x24 tokenized US stock perception, after-hours macro pricing, and delta hedging."""

    def __init__(self):
        self.name = "Core 6 - Tokenized US Stocks Agent"

    def scan_us_equities(self) -> Dict[str, Any]:
        memory.log(self.name, "Scanning 7x24 tokenized US stock contracts on Bitget", LogLevel.INFO)
        return scan_tokenized_stocks()

    def check_after_hours_divergence(self, stock_symbol: str = "NVDAUSDT") -> Dict[str, Any]:
        return detect_after_hours_spread(stock_symbol=stock_symbol)

    def execute_delta_hedge(
        self,
        crypto_symbol: str = "BTCUSDT",
        stock_symbol: str = "SPYUSDT",
        amount_usdt: float = 200.0
    ) -> Dict[str, Any]:
        return execute_cross_asset_hedge(crypto_symbol, stock_symbol, amount_usdt)


tokenized_stocks_agent = TokenizedStocksAgent()
