"""Core 3: Backtesting Agent - Historical Strategy Simulations."""

from typing import Any, Dict
from bitget_skills_hub.backtesting.tools import run_strategy_backtest, compare_strategies
from src.core.memory import memory, LogLevel


class BacktestAgent:
    """Specialist sub-agent for verifying strategy hypotheses before capital allocation."""

    def __init__(self):
        self.name = "Core 3 - Backtesting Engine"

    def run_backtest(
        self,
        symbol: str = "NVDAUSDT",
        strategy_name: str = "RSI_MEAN_REVERSION",
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        memory.log(self.name, f"Simulating {strategy_name} on {symbol} with ${initial_capital:.2f}", LogLevel.INFO)
        res = run_strategy_backtest(symbol=symbol, strategy_name=strategy_name, initial_capital=initial_capital)

        summary = (
            f"Backtest of {strategy_name} on {symbol}: Net Return {res.get('return_pct')}% "
            f"(Alpha over Benchmark: +{res.get('alpha_pct')}%), Sharpe Ratio: {res.get('sharpe_ratio')}, "
            f"Max Drawdown: {res.get('max_drawdown_pct')}%, Win Rate: {res.get('win_rate_pct')}%, "
            f"Profit Factor: {res.get('profit_factor')} across {res.get('total_trades')} trades."
        )

        return {
            "core": self.name,
            "symbol": symbol.upper(),
            "strategy": strategy_name,
            "performance": res,
            "synthesis": summary
        }

    def compare_all_strategies(self, symbol: str = "NVDAUSDT") -> Dict[str, Any]:
        return compare_strategies(symbol=symbol)


backtest_agent = BacktestAgent()
