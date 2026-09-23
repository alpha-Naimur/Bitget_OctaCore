"""Market Intelligence and Order Book depth analysis tools."""

from typing import Any, Dict
from src.bitget.market_data import market_data


def get_order_book_depth(symbol: str = "BTCUSDT", limit: int = 15) -> Dict[str, Any]:
    """Retrieve order book depth and evaluate bid/ask volume imbalance."""
    return market_data.get_order_book_depth(symbol=symbol, limit=limit)


def get_market_overview() -> Dict[str, Any]:
    """Fetch real-time market overview covering Crypto and 7x24 Tokenized US Equities."""
    return market_data.get_market_overview()


def get_ticker_price(symbol: str) -> Dict[str, Any]:
    """Fetch latest market price for a symbol."""
    price = market_data.get_ticker_price(symbol)
    return {
        "symbol": symbol.upper(),
        "price": price,
        "available": price is not None
    }
