"""Tokenized US Stocks (7x24) perception and cross-asset execution tools."""

import time
from typing import Any, Dict, List, Optional
from src.bitget.market_data import market_data, TOKENIZED_US_STOCKS
from src.bitget.trading_engine import trading_engine
from src.core.memory import memory, LogLevel


def scan_tokenized_stocks() -> Dict[str, Any]:
    """Scan all 7x24 Tokenized US Equities available on Bitget for price action, volume, and momentum."""
    results = []
    for symbol in TOKENIZED_US_STOCKS:
        price = market_data.get_ticker_price(symbol)
        if price:
            ta = market_data.compute_technical_analysis(symbol, granularity="1H")
            cached = market_data.ticker_cache.get(symbol, {})
            results.append({
                "symbol": symbol,
                "asset": symbol.replace("USDT", ""),
                "price": price,
                "change_24h": cached.get("change24h", 0.0),
                "volume_usdt": cached.get("volume_usdt", 0.0),
                "rsi": ta.get("rsi_14", 50.0),
                "bias": ta.get("bias", "NEUTRAL"),
                "trading_window": "7x24_CONTINUOUS"
            })

    results.sort(key=lambda x: abs(x["change_24h"]), reverse=True)

    return {
        "timestamp": time.time(),
        "total_us_stocks_tracked": len(results),
        "stocks": results,
        "market_status": "OPEN_7x24_ON_BITGET"
    }


def detect_after_hours_spread(stock_symbol: str = "NVDAUSDT") -> Dict[str, Any]:
    """Detect after-hours and weekend macro divergence between tokenized stocks and benchmark crypto."""
    stock_symbol = stock_symbol.upper()
    stock_price = market_data.get_ticker_price(stock_symbol) or 100.0
    btc_price = market_data.get_ticker_price("BTCUSDT") or 90000.0

    stock_ta = market_data.compute_technical_analysis(stock_symbol)
    btc_ta = market_data.compute_technical_analysis("BTCUSDT")

    stock_rsi = stock_ta.get("rsi_14", 50.0)
    btc_rsi = btc_ta.get("rsi_14", 50.0)
    rsi_spread = round(stock_rsi - btc_rsi, 2)

    opportunity = "NORMAL"
    if rsi_spread > 25.0:
        opportunity = f"{stock_symbol} Outperforming Crypto Divergence (Potential Mean-Reversion Hedge)"
    elif rsi_spread < -25.0:
        opportunity = f"{stock_symbol} Deep Discount relative to Crypto (Accumulation Window)"

    return {
        "stock_symbol": stock_symbol,
        "stock_price": stock_price,
        "stock_rsi": stock_rsi,
        "btc_rsi": btc_rsi,
        "rsi_divergence": rsi_spread,
        "regime_opportunity": opportunity,
        "trading_advantage": "7x24 execution allows pricing weekend macro surprises before NYSE open."
    }


def execute_cross_asset_hedge(
    crypto_symbol: str = "BTCUSDT",
    stock_symbol: str = "SPYUSDT",
    hedge_amount_usdt: float = 200.0
) -> Dict[str, Any]:
    """Execute autonomous cross-asset delta hedge between Crypto and Tokenized US Stock contract."""
    memory.log("CrossAsset", f"Initiating delta hedge: Long {crypto_symbol} vs Short {stock_symbol}", LogLevel.INFO)
    
    # 1. Buy Crypto spot
    crypto_res = trading_engine.execute_spot_order(
        symbol=crypto_symbol,
        side="BUY",
        amount_usdt=hedge_amount_usdt / 2.0,
        reason=f"Cross-Asset Hedge Leg 1: Long {crypto_symbol}",
        agent_core="Core 6 - Tokenized US Stocks Agent"
    )

    # 2. Short US Stock futures hedge
    stock_res = trading_engine.execute_futures_order(
        symbol=stock_symbol,
        side="SELL",
        amount_usdt=hedge_amount_usdt / 2.0,
        leverage=5,
        reason=f"Cross-Asset Hedge Leg 2: Short {stock_symbol}",
        agent_core="Core 6 - Tokenized US Stocks Agent"
    )

    return {
        "hedge_status": "EXECUTED",
        "leg1_crypto": crypto_res,
        "leg2_stock_futures": stock_res,
        "total_notional_hedged_usdt": hedge_amount_usdt
    }
