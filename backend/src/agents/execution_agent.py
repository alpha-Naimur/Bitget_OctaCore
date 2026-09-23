"""Core 5: Execution Agent - Order Routing, Smart DCA, and Portfolio Telemetry."""

from typing import Any, Dict, Optional
from bitget_skills_hub.agentic_trading.tools import (
    execute_spot_order,
    execute_futures_order,
    execute_smart_dca,
    get_portfolio_status,
    switch_execution_mode
)
from src.core.memory import memory, LogLevel


class ExecutionAgent:
    """Specialist sub-agent managing order execution, volatility-scaled Smart DCA, and balances."""

    def __init__(self):
        self.name = "Core 5 - Execution Agent"

    def execute_spot(
        self,
        symbol: str,
        side: str,
        amount_usdt: Optional[float] = None,
        quantity: Optional[float] = None,
        reason: str = "Execution Core"
    ) -> Dict[str, Any]:
        return execute_spot_order(symbol=symbol, side=side, amount_usdt=amount_usdt, quantity=quantity, reason=reason)

    def execute_futures(
        self,
        symbol: str,
        side: str,
        amount_usdt: float,
        leverage: int = 10,
        reason: str = "Execution Core"
    ) -> Dict[str, Any]:
        return execute_futures_order(symbol=symbol, side=side, amount_usdt=amount_usdt, leverage=leverage, reason=reason)

    def run_smart_dca(self, symbol: str, base_amount_usdt: float = 100.0) -> Dict[str, Any]:
        return execute_smart_dca(symbol=symbol, base_dca_amount_usdt=base_amount_usdt)

    def get_portfolio(self) -> Dict[str, Any]:
        return get_portfolio_status()


execution_agent = ExecutionAgent()
