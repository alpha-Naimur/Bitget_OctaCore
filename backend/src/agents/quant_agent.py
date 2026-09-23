"""Core 2: Quant Analyst Agent - Downside Risk, Hurst Exponent, and Markowitz MPT."""

from typing import Any, Dict, List, Optional
from bitget_skills_hub.quant_engine.tools import (
    get_quant_risk_metrics,
    get_time_series_regime,
    optimize_portfolio_weights,
    get_composite_alpha_score
)
from src.core.memory import memory, LogLevel


class QuantAnalystAgent:
    """Specialist sub-agent for institutional factor risk, Hurst regime detection, and MPT optimization."""

    def __init__(self):
        self.name = "Core 2 - Quant Engine"

    def analyze_risk_and_regime(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        memory.log(self.name, f"Deconstructing tail risk and Hurst regime for {symbol}", LogLevel.INFO)
        quant = get_quant_risk_metrics(symbol=symbol)
        regime = get_time_series_regime(symbol=symbol)
        alpha = get_composite_alpha_score(symbol=symbol)

        summary = (
            f"{symbol} Tail Risk: 1H VaR(95%) is {quant.get('var_95_pct')}% with Expected Shortfall (CVaR) of {quant.get('cvar_95_pct')}%. "
            f"Hurst Exponent is {regime.get('hurst_exponent')} ({regime.get('regime')}, OU Half-Life: {regime.get('half_life_hours')}h). "
            f"Alpha Factor Score: {alpha.get('alpha_score')} ({alpha.get('action_recommendation')})."
        )

        return {
            "core": self.name,
            "symbol": symbol.upper(),
            "quant_metrics": quant,
            "regime_model": regime,
            "alpha_factors": alpha,
            "synthesis": summary
        }

    def optimize_portfolio(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        return optimize_portfolio_weights(symbols=symbols)


quant_agent = QuantAnalystAgent()
