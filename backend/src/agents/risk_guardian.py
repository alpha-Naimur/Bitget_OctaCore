"""Core 4: Risk Guardian Agent - Mathematical Safety Firewall & Kill-Switch."""

from typing import Any, Dict
from bitget_skills_hub.risk_guardian.tools import (
    validate_trade_risk,
    trigger_emergency_kill_switch,
    deactivate_kill_switch,
    get_risk_firewall_status
)
from src.core.memory import memory, LogLevel


class RiskGuardianAgent:
    """Specialist sub-agent for pre-trade capital protection and emergency circuit breakers."""

    def __init__(self):
        self.name = "Core 4 - Risk Guardian"

    def audit_trade(self, symbol: str, side: str, amount_usdt: float) -> Dict[str, Any]:
        check = validate_trade_risk(symbol=symbol, side=side, amount_usdt=amount_usdt)
        if not check.get("approved"):
            memory.log(self.name, f"Order REJECTED: {check.get('reason')}", LogLevel.WARN)
        else:
            memory.log(self.name, f"Order APPROVED for {side} {symbol} (${amount_usdt:.2f})", LogLevel.INFO)
        return check

    def emergency_halt(self) -> Dict[str, Any]:
        return trigger_emergency_kill_switch()

    def resume_operations(self) -> Dict[str, Any]:
        return deactivate_kill_switch()

    def get_status(self) -> Dict[str, Any]:
        return get_risk_firewall_status()


risk_guardian_agent = RiskGuardianAgent()
