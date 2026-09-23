"""Agentic Trading execution tools for Spot, Futures, and Smart DCA."""

from typing import Any, Dict, Optional
from src.bitget.trading_engine import trading_engine
from src.bitget.simulator import simulator
from bitget_skills_hub.risk_guardian.tools import validate_trade_risk
from src.core.config import ExecutionMode


def execute_spot_order(
    symbol: str,
    side: str,
    amount_usdt: Optional[float] = None,
    quantity: Optional[float] = None,
    reason: str = "Agentic Spot Trade"
) -> Dict[str, Any]:
    """Execute spot order with mandatory pre-trade risk firewall verification."""
    symbol = symbol.upper()
    side = side.upper()
    est_amount = amount_usdt or 100.0

    # Risk Check
    risk = validate_trade_risk(symbol, side, est_amount)
    if not risk.get("approved"):
        return {"success": False, "error": risk.get("reason"), "risk_violation": True}

    return trading_engine.execute_spot_order(
        symbol=symbol,
        side=side,
        amount_usdt=amount_usdt,
        quantity=quantity,
        reason=reason,
        agent_core="Core 5 - Execution Agent"
    )


def execute_futures_order(
    symbol: str,
    side: str,  # BUY | SELL
    amount_usdt: float,
    leverage: int = 10,
    reason: str = "Agentic Futures Contract"
) -> Dict[str, Any]:
    """Execute Mix Futures contract order (Crypto or 7x24 Tokenized US Stocks)."""
    symbol = symbol.upper()
    side = side.upper()

    # Risk Check
    risk = validate_trade_risk(symbol, side, amount_usdt)
    if not risk.get("approved"):
        return {"success": False, "error": risk.get("reason"), "risk_violation": True}

    return trading_engine.execute_futures_order(
        symbol=symbol,
        side=side,
        amount_usdt=amount_usdt,
        leverage=leverage,
        reason=reason,
        agent_core="Core 5 - Execution Agent"
    )


def close_futures_position(
    symbol: str,
    side: Optional[str] = None,
    reason: str = "Autonomous Futures Position Close"
) -> Dict[str, Any]:
    """Close an active futures position (LONG or SHORT) for a given symbol.

    If no running position is found, returns found=False with guidance.
    """
    return trading_engine.close_futures_position(
        symbol=symbol,
        side=side,
        reason=reason,
        agent_core="Core 5 - Execution Agent"
    )


def execute_smart_dca(
    symbol: str,
    base_dca_amount_usdt: float = 100.0
) -> Dict[str, Any]:
    """Execute volatility-scaled Smart DCA with oversold dip accumulation."""
    return trading_engine.execute_smart_dca(
        symbol=symbol,
        base_dca_amount_usdt=base_dca_amount_usdt,
        agent_core="Core 5 - Execution Agent"
    )


def get_portfolio_status() -> Dict[str, Any]:
    """Fetch live portfolio balances, PnL, holdings, and allocations."""
    return trading_engine.get_portfolio()


def switch_execution_mode(mode: str) -> Dict[str, Any]:
    """Switch execution mode: SIMULATION, TESTNET, MAINNET, or SUB_ACCOUNT."""
    try:
        new_mode = ExecutionMode(mode.upper())
        trading_engine.set_execution_mode(new_mode)
        return {
            "success": True,
            "current_mode": new_mode.value,
            "message": f"Successfully changed execution mode to {new_mode.value}"
        }
    except ValueError:
        valid_modes = [m.value for m in ExecutionMode]
        return {
            "success": False,
            "error": f"Invalid mode '{mode}'. Supported modes: {', '.join(valid_modes)}"
        }
