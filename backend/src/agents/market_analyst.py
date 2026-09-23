"""Core 1: Market Analyst Agent - Technical Analysis & Order Book Depth."""

from typing import Any, Dict
from bitget_skills_hub.market_intelligence.tools import get_order_book_depth, get_market_overview
from bitget_skills_hub.bitget_signal.tools import get_technical_analysis
from src.core.memory import memory, LogLevel


class MarketAnalystAgent:
    """Specialist sub-agent for multi-period Technical Analysis and Liquidity Imbalance."""

    def __init__(self):
        self.name = "Core 1 - Market Analyst"

    def analyze(self, symbol: str = "BTCUSDT", interval: str = "1H") -> Dict[str, Any]:
        memory.log(self.name, f"Analyzing technicals and order book depth for {symbol} ({interval})", LogLevel.INFO)
        ta = get_technical_analysis(symbol=symbol, interval=interval)
        depth = get_order_book_depth(symbol=symbol, limit=15)

        summary = (
            f"{symbol} is currently {ta.get('bias', 'NEUTRAL')} at ${ta.get('current_price', 0):.4f}. "
            f"RSI(14) is {ta.get('rsi_14', 50):.1f}. Order book liquidity skew is {depth.get('liquidity_skew', 'BALANCED')} "
            f"(Bid/Ask Depth Ratio: {depth.get('depth_ratio', 1.0):.2f})."
        )

        return {
            "core": self.name,
            "symbol": symbol.upper(),
            "technical_analysis": ta,
            "order_book_depth": depth,
            "synthesis": summary
        }


market_analyst_agent = MarketAnalystAgent()
