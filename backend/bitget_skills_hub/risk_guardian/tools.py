"""Pre-trade risk firewall, circuit breakers, and emergency kill-switch tools."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from src.bitget.simulator import simulator
from src.bitget.trading_engine import trading_engine
from src.core.config import settings
from src.core.memory import memory, LogLevel


def validate_trade_risk(
    symbol: str,
    side: str,
    amount_usdt: float
) -> Dict[str, Any]:
    """Mathematical pre-trade firewall verifying order caps, exposure limits, and drawdown halts."""
    symbol = symbol.upper()
    side = side.upper()

    # 1. Kill switch check
    if trading_engine.kill_switch_active or simulator.kill_switch_triggered:
        return {
            "approved": False,
            "reason": "REJECTED: Emergency Kill-Switch is active. All trading halted.",
            "risk_score": 100
        }

    # 2. Single Order Cap ($500 default)
    if amount_usdt > settings.MAX_SINGLE_ORDER_USD:
        return {
            "approved": False,
            "reason": f"REJECTED: Order size ${amount_usdt:.2f} exceeds MAX_SINGLE_ORDER_USD limit of ${settings.MAX_SINGLE_ORDER_USD:.2f}.",
            "risk_score": 85
        }

    # 3. Portfolio Drawdown Halt (5% default)
    portfolio = simulator.get_portfolio_summary()
    total_pnl_pct = portfolio.get("total_pnl_percent", 0.0)
    if total_pnl_pct < -settings.MAX_DRAWDOWN_PERCENT:
        return {
            "approved": False,
            "reason": f"REJECTED: Portfolio drawdown ({abs(total_pnl_pct):.2f}%) exceeds max threshold of {settings.MAX_DRAWDOWN_PERCENT}%. Trading paused.",
            "risk_score": 90
        }

    # 4. Single Asset Exposure Cap ($1000 default)
    if side == "BUY":
        existing_val = 0.0
        for h in portfolio.get("holdings", []):
            if h.get("symbol") == symbol:
                existing_val += h.get("value_usdt", 0.0)

        if (existing_val + amount_usdt) > settings.MAX_POSITION_SIZE_USD:
            return {
                "approved": False,
                "reason": f"REJECTED: Resulting {symbol} exposure (${existing_val + amount_usdt:.2f}) exceeds MAX_POSITION_SIZE_USD (${settings.MAX_POSITION_SIZE_USD:.2f}).",
                "risk_score": 75
            }

    # 5. Daily Trade Limit
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_trades = [t for t in memory.trades if t.status == "FILLED" and str(t.timestamp).startswith(today_str)]
    if len(today_trades) >= settings.DAILY_TRADE_LIMIT:
        return {
            "approved": False,
            "reason": f"REJECTED: Daily trade limit of {settings.DAILY_TRADE_LIMIT} orders reached.",
            "risk_score": 60
        }

    return {
        "approved": True,
        "reason": "APPROVED: All mathematical risk checks passed.",
        "risk_score": 15,
        "symbol": symbol,
        "amount_usdt": amount_usdt,
        "current_drawdown_pct": round(abs(min(0.0, total_pnl_pct)), 2)
    }


def trigger_emergency_kill_switch() -> Dict[str, Any]:
    """Trigger 1-click Emergency Kill-Switch, liquidating all open positions to USDT."""
    return trading_engine.trigger_kill_switch()


def deactivate_kill_switch() -> Dict[str, Any]:
    """Deactivate emergency kill-switch and restore operational status."""
    return trading_engine.deactivate_kill_switch()


def get_risk_firewall_status() -> Dict[str, Any]:
    """Retrieve telemetry on current risk limits and utilization."""
    portfolio = simulator.get_portfolio_summary()
    total_val = portfolio.get("total_value_usdt", 10000.0)
    total_pnl_pct = portfolio.get("total_pnl_percent", 0.0)
    kill_switch = trading_engine.kill_switch_active or simulator.kill_switch_triggered
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "kill_switch_active": kill_switch,
        "firewall_status": "LOCKED" if kill_switch else "ACTIVE_PROTECTION",
        "limits": {
            "max_single_order_usd": settings.MAX_SINGLE_ORDER_USD,
            "max_position_size_usd": settings.MAX_POSITION_SIZE_USD,
            "max_drawdown_percent": settings.MAX_DRAWDOWN_PERCENT,
            "daily_trade_limit": settings.DAILY_TRADE_LIMIT
        },
        "current_metrics": {
            "portfolio_value_usdt": total_val,
            "current_drawdown_pct": round(abs(min(0.0, total_pnl_pct)), 2),
            "trades_today_count": len([t for t in memory.trades if t.status == "FILLED" and str(t.timestamp).startswith(today_str)]),
            "drawdown_limit_breached": total_pnl_pct < -settings.MAX_DRAWDOWN_PERCENT
        }
    }
